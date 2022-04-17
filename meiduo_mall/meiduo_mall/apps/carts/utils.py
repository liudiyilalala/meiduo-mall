import base64
import pickle

from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, user, response):
    """
    合并请求用户的购物车数据，将未登录保存在cookie里的保存到redis中
    遇到cookie与redis中出现相同的商品时以cookie数据为主，覆盖redis中的数据
    :param request: 用户的请求对象
    :param user: 当前登录的用户
    :param response: 响应对象，用于清楚购物车cookie
    :return:
    """
    # 获取cookie中的购物车
    cookie_cart = request.COOKIES.get('cart')
    if not cookie_cart:
        return response

    # 解析cookie购物车数据
    cookie_cart = pickle.loads(base64.b64decode(cookie_cart.encode()))

    # "sku_id1": {
    #     "count": "1",
    #     "selected": "True"
    # },
    # 新建新的购物车字典数据
    new_cart_dict = {}
    # 新建新的勾选状态列表，用于如果cookie中有勾选状态的添加其中，并保存到redis中
    new_selected_add = []
    # 新建未勾选状态的列表，用于如果没有勾选的商品添加到其中，并保存到redis
    new_selected_remove = []
    # 将cookie取出的字典数据变为sku_id: count类型, 并加入到new_cart_dict
    for sku_id, cart_dict in cookie_cart.items():
        new_cart_dict[sku_id] = cart_dict['count']

        # 如果cookie数据中有selected为true，将sku_id添加到new_selected_add中
        if cart_dict['selected']:
            new_selected_add.append(sku_id)
        else:
            # 如果为false，则添加到new_selected_remove中
            new_selected_remove.append(sku_id)

    # 建立redis链接
    redis_conn = get_redis_connection('cart')
    pl = redis_conn.pipeline()

    # 将new_cart_dict中的数据保存到redis。即将cookie中的数据保存到redis，并覆盖掉已存在的
    pl.hmset('carts_userid_%s' % user.id, new_cart_dict)
    # 如果new_selected_add有值，保存到redis
    if new_selected_add:
        pl.sdd('selected_userid_%s' % user.id, *new_selected_add)
    # 如果new_selected_remove有值，即表示数据未勾选，须将redis selected中勾选的数据删掉
    if new_selected_remove:
        pl.srem('selected_userid_%s' % user.id, *new_selected_remove)

    pl.execute()

    # 清除cookie
    response.delete_cookie('cart')

    return response


# def merge_cart_cookie_to_redis(request, user, response):
#     """
#     合并请求用户的购物车数据，将未登录保存在cookie里的保存到redis中
#     遇到cookie与redis中出现相同的商品时以cookie数据为主，覆盖redis中的数据
#     :param request: 用户的请求对象
#     :param user: 当前登录的用户
#     :param response: 响应对象，用于清楚购物车cookie
#     :return:
#     """
#     # 获取cookie中的购物车
#     cookie_cart = request.COOKIES.get('cart')
#     if not cookie_cart:
#         return response
#
#     # 解析cookie购物车数据
#     cookie_cart = pickle.loads(base64.b64decode(cookie_cart.encode()))
#
#     # 获取redis中购物车数据
#     redis_conn = get_redis_connection('cart')
#     redis_cart = redis_conn.hgetall('cart_%s' % user.id)
#
#     # 用于保存最终购物车数据的字典
#     cart = {}
#
#     # 将redis中购物车数据的键值对转换为整型
#     for sku_id, count in redis_cart.items():
#         cart[int(sku_id)] = int(count)
#
#     # 记录redis勾选状态中应该增加的sku_id
#     redis_cart_selected_add = []
#
#     # 记录redis勾选状态中应该删除的sku_id
#     redis_cart_selected_remove = []
#
#     # 合并cookie购物车与redis购物车，保存到cart字典中
#     for sku_id, count_selected_dict in cookie_cart.items():
#         # 处理商品数量
#         cart[sku_id] = count_selected_dict['count']
#
#         if count_selected_dict['selected']:
#             redis_cart_selected_add.append(sku_id)
#         else:
#             redis_cart_selected_remove.append(sku_id)
#
#     if cart:
#         pl = redis_conn.pipeline()
#         pl.hmset('cart_%s' % user.id, cart)
#         if redis_cart_selected_add:
#             pl.sadd('cart_selected_%s' % user.id, *redis_cart_selected_add)
#         if redis_cart_selected_remove:
#             pl.srem('cart_selected_%s' % user.id, *redis_cart_selected_remove)
#         pl.execute()
#
#     response.delete_cookie('cart')
#
#     return response


