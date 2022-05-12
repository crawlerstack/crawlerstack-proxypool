# TODOS

## 下载器的代理IP配置优化

由于现在下载器使用的是 httpx 库，在设置代理是只能通过 client 初始化，并不会配置到 requests 对象上。

当前的操作是在请求发起前，将代理IP配置在 request.extensions.proxy 中，然后在 response.request 中获取。
但是在业务逻辑（比如 checker ） 中也需要这么操作。

这种获取方式太耦合了 httpx 库，因为使用了 request.extensions 存储。

优化思路：

使用 response 代理对象，并将 response 代理对象的 request 设置为 request 代理对象。