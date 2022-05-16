import functools
from collections.abc import AsyncGenerator, Callable
from typing import Type, TypeVar

from fastapi import Request

from crawlerstack_proxypool.service import CRUDMixin

RT = TypeVar('RT', bound=CRUDMixin)


def service_depend(service_kls: Type[RT]) -> Callable[[Request], AsyncGenerator[RT, None]]:
    """
    Service dependency
    :param service_kls:
    :return:
    """

    async def get_service(request: Request):
        """service factory"""
        db = request.app.extra.get('db')
        async with db.scoped_session() as local_session:
            try:
                async with local_session.begin():
                    yield service_kls(local_session)
            finally:
                await local_session.close()

    return get_service


def auto_commit(func: Callable):
    """
    为了解决 fastapi 的 Depends 无法自动提交，额外做了一个逻辑
    在视图函数阶段，对该视图函数中的逻辑手动做自动提交。

    虽然 service_depend 会生成一个已经包含了开启事务 `local_session.begin()` 的
    session ，但是由于 Depends 的机制，它只会在 `fastapi.routing.get_request_handler`
    完成后才会执行 Depends 中 yield 之后的逻辑。这将导致在 `get_request_handler` 中使用
    `response_model` 无法正常序列化返回值。因为数据库操作并没有提交，所以，像创建操作的对象
    根本就没有 id 值。

     `fastapi.routing.get_request_handler` 的逻辑中，会在执行完视图函数后，将事务提交。
     这样错有的操作进入数据库，返回值会进入 `serialize_response` 函数，根据返回值的 Schema
     进行序列化。

     我认为这个 `fastapi.routing.get_request_handler` 的逻辑有问题，或者是 Depends 的
     设计有问题。因为现在的机制无法在序列化之前将事务提交。

     ref: https://docs.sqlalchemy.org/en/14/orm/contextual.html#using-thread-local-scope-with-web-applications

    :param func:
    :return:
    """

    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        service = kwargs.get('service')

        if service:
            try:
                result = await func(*args, **kwargs)
                await service.session.commit()
            except Exception as ex:
                await service.session.rollback()
                raise ex
        else:
            result = await func(*args, **kwargs)
        return result

    return _wrapper
