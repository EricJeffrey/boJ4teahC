服务器转发消息的小工具，可以转发截屏、文字数据

后端使用C++编写，使用`epoll`事件模型处理连接，但数据读取和发送部分没有很好地处理可能的异常情况

前端采用Python编写，使用了各种包如剪贴板、pillow，基本开发完成，但需要注意**不要在一个系统上同时使用helper和worker**.

后端依赖: `epoll`

前端python3依赖: `pywin32, keyboard, pillow`
