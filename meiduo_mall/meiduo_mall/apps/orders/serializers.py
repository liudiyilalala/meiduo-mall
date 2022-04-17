from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

from goods.models import SKU
from orders.models import OrderInfo, OrderGoods

"""
返回数据如下：
{
    "freight":"10.00",
    "skus":[
        {
            "id":10,
            "name":"华为 HUAWEI P10 Plus 6GB+128GB 钻雕金 移动联通电信4G手机 双卡双待",
             "default_image_url":"http://image.meiduo.site:8888/group1/M00/00/02/CtM3BVrRchWAMc8rAARfIK95am88158618",
            "price":"3788.00",
            "count":1
        },
        {
            "id":16,
            "name":"华为 HUAWEI P10 Plus 6GB+128GB 曜石黑 移动联通电信4G手机 双卡双待",
            "default_image_url":"http://image.meiduo.site:8888/group1/M00/00/02/CtM3BVrRdPeAXNDMAAYJrpessGQ9777651",
            "price":"3788.00",
            "count":1
        }
    ]
}

"""


class CartSKUSerializer(serializers.ModelSerializer):
    """
    购物车商品数据序列化器
    """
    count = serializers.IntegerField(label='数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')


class OrderSettlementSerializer(serializers.Serializer):
    """
    订单结算数据序列化器
    """
    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)


class SaveOrderSerializer(serializers.ModelSerializer):
    """
        下单数据序列化器
        """

    class Meta:
        model = OrderInfo
        fields = ('order_id', 'address', 'pay_method')
        read_only_fields = ('order_id',)
        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True,
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        # 获取当前下单用户
        user = self.context['request'].user
        # 生成订单编号
        # 组织订单编号 20170903153611+user.id
        # timezone.now() -> datetime
        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        # 获取前端传来的数据
        address = validated_data['address']
        pay_method = validated_data['pay_method']

        """在保存订单数据中，涉及到多张表（OrderInfo、OrderGoods、SKU）的数据修改，
        对这些数据的修改应该是一个整体事务，即要么一起成功，要么一起失败。
        """
        with transaction.atomic():
            # 创建保存点
            save_id = transaction.savepoint()
            # 保存订单基本信息数据 OrderInfo
            try:
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal(0),
                    freight=Decimal(10),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH'] else
                                    OrderInfo.ORDER_STATUS_ENUM['UNPAID']
            )
            # 从redis中获取购物车结算商品数据
                # 从redis中获取购物车sku_id
                redis_conn = get_redis_connection('cart')
                # 获取购物车商品id和数量
                redis_cart = redis_conn.hgetall('carts_userid_%s' % user.id)
                # 获取勾选状态的数据
                redis_selected = redis_conn.smembers("selected_userid_%s" % user.id)
                # 提取出勾选状态的购物车数据
                cart_dict = {}
                for sku_id in redis_selected:
                    cart_dict[int(sku_id)] = int(redis_cart[sku_id])
                # 遍历结算商品：
                sku_id_list = cart_dict.keys()
                # skus = SKU.objects.filter(id__in=sku_id_list)
                for sku_id in sku_id_list:

                    while True:
                        # 查询商品信息
                        sku = SKU.objects.get(id=sku_id)
                        #  获取当前商品的购买数量
                        sku_count = cart_dict[sku.id]
                        # 判断商品库存是否充足  当前购买数量 < 商品总数
                        # 获取当前商品的总数量
                        now_stock = sku.stock
                        # 获取当前商品销量
                        now_sales = sku.sales
                        if sku_count > now_stock:
                            # 表示商品购买数量大于库存数量，需要回滚事务，并返回错误
                            # 回滚到保存点
                            transaction.savepoint_rollback(save_id)
                            raise serializers.ValidationError("商品%s库存不足" % sku.name)

                        # 减少商品库存，增加商品销量
                        new_stock = now_stock - sku_count
                        # 增加销量
                        new_sales = now_sales + sku_count

                        """
                        在多个用户同时发起对同一个商品的下单请求时，先查询商品库存，再修改商品库存，会出现资源竞争问题，导致库存的最终结果
                        出现异常。
                        需要使用乐观锁来解决这一现象
                        乐观锁并不是真实存在的锁，而是在更新的时候判断此时的库存是否是之前查询出的库存，如果相同，表示没人修改，可以更新库存，
                        否则表示别人抢过资源，不再执行库存更新。
                        """
                        result = SKU.objects.filter(id=sku.id, stock=now_stock).update(stock=new_stock, sales=new_sales)

                        if result == 0:
                            # 表示更新失败，结束本次循环，进入下一次循环
                            continue

                        # 修改订单基本信息数据 OrderInfo 的total_count和total_amount
                        order.total_count += sku_count
                        order.total_amount += (sku.price * sku_count)

                        # 保存订单商品数据 OrderGoods
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price,
                        )

                        # 保存成功之后跳出while循环，进入for循环
                        break

                # 数据保存
                order.save()
            except serializers.ValidationError:
                raise
            except Exception as e:
                # 回滚到保存点
                transaction.savepoint_rollback(save_id)
                raise
            else:
                # 提交事务
                transaction.savepoint_commit(save_id)

        # 在redis购物车中删除已计算商品数据
        pl = redis_conn.pipeline()

        # 删除cart中数据 ,即勾选的sku_id数据
        pl.hdel('carts_userid_%s' % user.id, *redis_selected)

        # 删除set中数据
        pl.srem('selected_userid_%s' % user.id, *redis_selected)

        pl.execute()

        # 返回orderINfo对象
        return order

