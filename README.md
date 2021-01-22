# crawlerstack-proxypool

这是一个通过收集网上免费代理 IP 为爬虫提供代理 IP 的程序

## TODO

- [ ] 优化原始代理到场景的写入数据格式。现在原始代理会自动加上 `http://` 和 `https://` 。现在需要确定 `http://` 的能否正常代理
 `https` 的网站， `https` 能否正常代理 `http` 网站。确定后， `RawIpPipeline` 写入逻辑。提高一级场景的效率。