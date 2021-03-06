## boJ4teahC实现

总体思路: **多类型客户端** + **服务端** 的方式。客户端分为 worker 和 helper。

用例和具体功能如下。

#### 用例

worker向服务端发送注册请求，注册完成后，worker将屏幕截图数据发送给服务端，表示需要广播该截图，服务端收到后将截图发给所有helper。helper在完成注册后，将数据发送给服务端，表示广播该数据。服务端就将helper的数据发送给所有的worker，worker在收到服务端数据后自动将其添加到系统剪贴板中。

#### 功能描述

- 服务端
  - 接收客户端注册请求
  - 将任意代码数据发送给所有客户端helper/worker
  - 将worker的截图数据发送给所有helper
- worker客户端
  - 获取屏幕截图并发送给服务端
  - 获取服务端发送的数据并自动加入剪贴板
- helper客户端
  - 将用户设置的代码数据发送给服务端
  - 获取服务端发送的截图数据并自动保存打开

#### 实现

- 服务端
  - 流程
    ```
    创建套接字启动监听
    开启子线程发送消息
      while true:
        取数据
        代码数据 - 发送给每个helper/worker
        截图数据 - 发送给每个helper
    Poller循环，监听事件
      while true:
        Poller.wait()
        新连接:
          accept并记录客户端套接字描述符
          监听新连接的读事件
        客户端数据可读:
          读取数据 - 解析为请求体
          判断请求体类型:
            1. 注册类型 - 确定类型，更新客户但集合
            2. worker的截图数据 - 获取数据，添加到helper的消息队列
            3. helper的代码数据 - 获取数据，添加到worker的消息队列
    ```
- 客户端 helper
  - 流程
    ```
    建立连接
    注册连接类型
    启动子线程循环
      while true:
        读取服务端数据
          代码数据 - 添加到剪贴板
          截图数据 - 保存到文件
    启动子线程循环
      while true:
        从代码队列取数据 - 发送到服务器
    开启UI循环
      用户点击粘贴代码 - 加入代码队列
    ```
- 客户端 worker
  - 流程
    ```
    建立连接
    注册连接类型
    启动子线程循环
      while true:
        从截图队列取数据 - 发送到服务端
        从代码队列取数据 - 发送到服务端
    注册键盘事件回调
      1. 截图并添加到截图队列
      2. 获取剪贴板代码并加入代码数据队列
    启动循环
      读取数据
        代码数据 - 添加到剪贴板，通知用户
    ```

#### 数据格式

**请求与响应采用同样的格式**:

```
首部: 请求码(4) + 请求体长度(4) + 保留字段(4)
请求体: 数据
```

**请求码类型**:

1. 心跳数据 100，长度 0
2. worker注册 101，长度 0
3. helper注册 102，长度 0
4. 截图数据 201
5. 代码数据 202
