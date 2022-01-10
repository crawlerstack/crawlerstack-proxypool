# crawlerstack-proxypool

这是一个通过收集网上免费代理 IP 为爬虫提供代理 IP 的程序

## Feature

- 配置驱动任务
- 解析器，校验器和爬虫逻辑支持扩展。

## TODO

- 抓取模块
- 爬虫模块
- 解析模块
- 任务调度
- 数据访问

## 思考

爬虫逻辑和任务逻辑如何调用，在有关数据访问的逻辑上如何调用？

```text
class Spider:
    
    request_queue: asyncio.Queue
    start_urls: list
    
    def start_request():
        将 url 加入到 queue 中
        
    def downloader():
        从队列中获取数据，然后下载
        
    def download_handler():
        真正下载的逻辑
        
    def parse():
```
