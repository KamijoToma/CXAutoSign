# CXAutoSign

## 背景

  由于本人是起床困难户，而屑学校每天都要求我们使用超星学习通的签到功能签到，来表示我们正在认真学习，所以在Github上大佬的启发下，结合我自己对超星网站的分析，以[Mkdir700/chaoxing_auto_sign](https://github.com/mkdir700/chaoxing_auto_sign)的[早期版本](https://github.com/KamijoToma/chaoxing_auto_sign)为基础，结合酷Q和[NoneBot](https://nonebot.cqp.moe/)的强大功能，写出了这一插件。

  在这个Git存储库上的`CXAutoSign`软件为本人同名私有软件的分支，原始版本暂不开源。

## 功能

* 硬编码的定时器签到
* 方便的全程基于QQ聊天的账号密码设定
* 仅管理员可用的好友白名单设定
* 基于`lambda`函数的好友个性化广播

## 部署细节

### 本地软件

首先需要安装[酷Q机器人](https://cqp.cc/forum.php)软件和[CQHTTP插件](https://cqhttp.cc/)。

在要部署本软件的电脑上安装Python3.8（不保证本软件能运行在低于3.8版本的Python上）

通过`pip`软件安装以下依赖库：

`nonebot motor requests httpx`

通常情况下安装最新版本即可。

### 数据库

在数据库所在的机器上安装`MongoDB`数据库，并创建如下结构

```
+---cxautosign
	|
	+--- users
	|
	+--- white_list
```

即创建一个包含`users`和`white_list`集合的名为`cxautosign`数据库

### 初始化本程序

首先，检查你收到的本程序源代码是否有以下基本结构：

```
│  bot.py
│  config.py
│
└─plugins
    └─CXAutoSign
            config.py
            data_source.py
            libcxsign.py
            __init__.py
```

然后，打开`/config.py`，填写超级管理员账号值，如有需要，也可一并更改`NoneBot`监听地址和端口。

打开`/plugins/CXAutoSign/config.py`，修改数据库地址和其他信息。

打开`/plugins/CXAutoSign/__init__.py`，定位至`269`行，修改定时任务执行时间。

将以上文件全部保存关闭，运行`/bot.py`，程序就会正常启动了。

## 命令

由于本软件是实验性软件，并没有使用`NLP`技术，所以采用命令方法改变机器人的设定。

| 命令格式                | 命令说明                                                     |
| ----------------------- | ------------------------------------------------------------ |
| help                    | 显示全局帮助信息。注意：管理员命令不会显示。                 |
| 自动签到                | 配置自动签到所使用的账号密码信息。一个账号只能登记一个       |
| 自动签到历史 [显示行数] | 显示本账号自动签到执行历史，仅显示签到成功的历史。参数显示行数为可选参数 |

Admin Only:

| 命令格式                     | 命令说明                                   |
| ---------------------------- | ------------------------------------------ |
| 查询验证信息 [显示条数]      | 查询好友白名单信息，显示条数为可选参数     |
| 广播消息                     | 交互式的发送单条广播消息，不支持个性化定制 |
| 添加验证信息 QQ号 [验证凭据] | 添加好友白名单验证信息，验证凭据为可选参数 |

## 技术细节

该插件基于[Mkdir700/chaoxing_auto_sign](https://github.com/mkdir700/chaoxing_auto_sign)早期版本，使用`async/await`技术，采用`mongodb`作为数据库……我编不下去了

其实就是一个女生自用的屑软件，50包邮，除了装逼什么用都没有……

### 定时器

使用的是`NoneBot`自带的屑定时器，动不动就`miss`，不晓得是什么原因，大概是RTC计时器精度不高罢……

直接用的`cron`定时任务。简单，方便，快捷，暴力。

定时器注解下面那行注释是开发环境DEBUG用的，不要在生产环境中用那条注解哦，搞出大新闻来，你自己可是要负责任的。

另外提一嘴，在代码里全局广播调用的是`datasource.broadcast_now(msg_gen)`。这里的`msg_gen`是一个函数，示例签名为`def msg_gen(user:dict) -> str`，参数是从数据库取出来的裸`user`行字典，返回值是个性化的文字。自评整个项目。这里我写的最好（滑稽）

```python
async def onCronTask():
    await datasource.broadcast_now(lambda user: f'Hello User {user.get("qq")}. Your CXAccount is {user.get("username")}.')
    pass
```

↑ 示例代码

如果要换成更加暴力的定时方式的话，直接在`callback`里调用`signv2`函数就行，带`v1`标签的是已经弃用的签到函数`v1`版本。

### 数据库

3月份听到某人的安利`MongoDB`所以试着用了这玩意，发现在这个项目上的确很好用，再也不用繁杂笨重的ORM框架了，直接一行json数据即可插入，还不用担心SQL注入，感觉很好用。这里安利一下。

至于驱动……这里用了`motor`，当时的感觉就是“wow， excited！异步处理这么高大上吗？我也要用一下，全都用上！”以至于选了`motor`还有`httpx`这两个支持异步的库，但是好像还是同步的速度。直到最近用`gevent`写项目，才发现异步效率不胜于同步的原因大概是方法用错了……不能无脑到处`async/await`……然而也不想改了，反正就要开学了，这屑软件就留在硬盘里吃灰罢。

## 版权声明

NoneBot软件采用MIT License:

```
The MIT License (MIT)
Copyright (c) 2018 Richard Chien

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

HTTPX软件使用BSD-3-Clause：

```
Copyright © 2019, [Encode OSS Ltd](https://www.encode.io/).
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
Terms
```

requests使用Apache License:

```
Copyright 2019 Kenneth Reitz

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       https://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```

Motor采用Apache2.0 License，协议地址为<http://www.apache.org/licenses/LICENSE-2.0>

本软件协议为Apache License 2.0，协议地址为<http://www.apache.org/licenses/LICENSE-2.0>

## 已知问题

* 软件定时器经常出现计时器超时从而导致函数调用失败：

```shell
Run time of job "checkTime (trigger: cron[year='[private]', month='[private]', day='[private]', week='[private]', day_of_week='[private]', hour='[private]', minute='[private]', second='[private]'], next run at: [private])" was missed by 0:00:02.290825
```

* 会将用户设定的自动回复解析为命令。这有可能造成潜在的Bug

## 报告问题

有关于代码方面的问题可以提Issue或者向我的邮箱发件：`icreamsky[at]protonmail.com`

