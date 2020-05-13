from nonebot import on_command, CommandSession, on_request, RequestSession
from motor.motor_asyncio import AsyncIOMotorClient
from nonebot.command.argfilter import extractors, validators
import nonebot
from . import config
import enum
from .data_source import perform_config, do_sign, getEvalData, sign_v2, welcome_new, broadcast_now
import datetime
import time

# I gently open the door.

class CXProcessEnum(enum.Enum):
    WELCOME = 1
    INFO_SELECT_LOGIN_METHOD = 2
    SELECT_LOGIN_METHOD = 7
    INFO_FID_CONFIG_FID = 3
    FID_CONFIG_FID = 8
    CONFIG_USER_NAME = 4
    CONFIG_PASSWORD = 5
    SUBMIT_DATA = 6
    CONFIRM_INFO = 9
    PROCESS_CONFIG = 10
    pass

# on_command 装饰器将函数声明为一个命令处理器
@on_command('autosign', aliases=('自动签到', '超星自动签到'))
async def autosign(session: CommandSession):
    # 超星自动签到配置函数
    status = session.get('status')
    if status == CXProcessEnum.WELCOME:
        await session.send("Hello！我是超星自动签到机器人，很高兴见到你。\n接下来我会引导你配置超星自动签到工具。")
        session.state['status'] = CXProcessEnum.INFO_SELECT_LOGIN_METHOD
        session.pause("接下来我要求你输入的参数必须加上“自动签到”这四个字加上一个空格，如果没有输入前缀程序就会炸掉。\n重复输入“自动签到”以继续配置进程")
        pass
    elif status == CXProcessEnum.SELECT_LOGIN_METHOD:
        await session.send("进程开始。接下来我会询问你几个问题用以配置签到任务。请认真阅读提示并回答。")
        await session.send("现在，你需要选择登录方式。登录方式有两种，一种是账号+密码登录，一种是学号+密码+学校ID登录。")
        await session.send("通过发送“自动签到 1”来选择以账号+密码方式登录，发送“自动签到 2”来选择以学号+密码+学校ID登录。")
        session.pause("输入命令以继续。")
    elif status == CXProcessEnum.FID_CONFIG_FID:
        fid = session.get("fid",prompt="请输入学校ID")
        await session.send(f"学校ID： {fid}")
        session.state['status'] = CXProcessEnum.CONFIG_USER_NAME
        session.pause("请输入用户名（学号），不允许有空格")
    elif status == CXProcessEnum.CONFIG_USER_NAME:
        username = session.get("username",prompt="请输入用户名")
        await session.send(f"用户名： {username}")
        session.state['status'] = CXProcessEnum.CONFIG_PASSWORD
        session.pause("请输入密码，不允许有空格")
        pass
    elif status == CXProcessEnum.CONFIG_PASSWORD:
        password = session.get("password",prompt="请输入密码")
        await session.send(f"密码位数： {len(password)}位")
        session.state['status'] = CXProcessEnum.CONFIRM_INFO
        session.pause("请再次确认以上信息是否正确，发送“自动签到 确认”以确认，发送“自动签到 放弃”以放弃此次更改\n提示：重新提交已经存在的用户将会修改该用户的密码")
        pass
    elif status == CXProcessEnum.PROCESS_CONFIG:
        await session.send("正在向数据库提交您的配置……")
        result = await perform_config(str(session.ctx['user_id']), session.state['username'], session.state['password'], session.state['fid'] if 'fid' in session.state else None)
        await session.send(f"您的配置已经提交到了数据库。\n调试信息：\n Database ID：{str(result)}\n\n执行出现问题时请凭调试信息联系我。")
        await session.send('配置进程已经顺利完成，如果想更新配置，请重新运行“自动签到”指令。\n您可通过运行“自动签到历史”指令来查看签到历史记录。\n如有问题请联系管理员。')
    session.finish()

@autosign.args_parser
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    arg_list = arg.split(" ")
    arg = arg_list[1] if len(arg_list) >= 2 else arg_list[0]

    if session.is_first_run:
        # 初始化环境变量
        session.state['status'] = CXProcessEnum.WELCOME
        session.state['method'] = 2
        pass
    elif session.state['status'] == CXProcessEnum.INFO_SELECT_LOGIN_METHOD:
        session.state['status'] = CXProcessEnum.SELECT_LOGIN_METHOD
    elif session.state['status'] == CXProcessEnum.SELECT_LOGIN_METHOD:
        if arg == '1' or arg == '2':
            session.state["status"] = CXProcessEnum.CONFIG_USER_NAME if arg == '1' else CXProcessEnum.FID_CONFIG_FID
            session.state['method'] = int(arg)
        else:
            session.pause("命令错误：请输入正确的选项")
            pass
    elif session.state['status'] == CXProcessEnum.FID_CONFIG_FID:
        if arg == '':
            session.pause("你没有输入学校ID！")
            pass
        session.state['fid'] = arg
    elif session.state['status'] == CXProcessEnum.CONFIG_USER_NAME:
        if arg == '':
            session.pause("你没有输入用户名！")
            pass
        session.state['username'] = arg
    elif session.state['status'] == CXProcessEnum.CONFIG_PASSWORD:
        if arg == '':
            session.pause("你没有输入密码！")
            pass
        await session.send("警告: 配置完成后请记得删除部分聊天记录，避免密码泄露！")
        session.state['password'] = arg
    elif session.state['status'] == CXProcessEnum.CONFIRM_INFO:
        if not arg == "确认":
            await session.send("已经取消配置进程。")
            session.finish()
            pass
        session.state['status'] = CXProcessEnum.PROCESS_CONFIG
        pass
    session.state["args"] = arg

@on_command('autosign_history', aliases=('自动签到历史', '超星自动签到历史', '签到历史'))
async def sign_history(session: CommandSession):
    h = session.state['history']
    await session.send("超星自动签到插件-执行历史查询模块")
    await session.send("注意：默认仅显示签到成功的历史记录，失败记录请联系管理员查询。\n通过在本命令后加上空格再加上数字即可显示指定条数的历史信息")
    history = await getEvalData(str(session.ctx['user_id']))
    history.reverse()
    await session.send(f'数据库查询成功，以下为最近成功的 {h} 条记录：')
    k = 0
    for i in history:
        if not i['succ']: continue
        k += 1
        timestamp = i['time']
        dateArray = datetime.datetime.fromtimestamp(timestamp)
        timenow = dateArray.strftime("%Y年%m月%d日 %H:%M:%S")
        result = str(i['result'])
        await session.send(f'======执行历史======\n* 时间：{timenow}\n* 签到标题：{result}')
        if k == h:break
        pass
    if k == 0:
        await session.send('啊偶，没有成功执行历史，是不是刚刚添加的还是执行失败了呢？\n\n如有疑问，请联系管理员。')
        pass
    session.finish()
    pass

@sign_history.args_parser
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    print(arg)
    arg_list = arg.split(" ")
    arg = arg_list[1] if len(arg_list) >= 2 else arg_list[0]
    if arg == '':
        session.state['history'] = config.MAX_HISTORY_DISPLAY
        pass
    else:
        try:
            h = abs(int(arg))
            h = h if not h == 0 else config.MAX_HISTORY_DISPLAY
        except:
            await session.send(f"错误的参数：{arg}")
            session.finish()
            pass
        session.state['history'] = h if h > 0 else config.MAX_HISTORY_DISPLAY
        pass
    session.state["args"] = arg
    pass

@on_command('help', aliases=('命令列表', '列表'))
async def command_help(session: CommandSession):
    await session.send(f"======命令列表======\n自动签到：配置和更新超星自动签到有关设定。\n自动签到历史：查看超星自动签到插件执行历史\n\n===========")
    session.finish()

@on_command('add_white_list_user', aliases=('添加验证信息'), permission=nonebot.permission.SUPERUSER)
async def command_add_whitelist_user(session: CommandSession):
    arg = session.current_arg_text.strip()
    arg_list = arg.split(" ")
    print(repr(arg_list))
    if len(arg_list) == 0:
        await session.send(f'格式：add_white_list_user USER_QQ COMMENT')
        session.finish()
    user_qq = int(arg_list[0])
    if len(arg_list) == 1:
        user_commit = ''
    else:
        user_commit = arg[1]
        pass
    conn = AsyncIOMotorClient(config.MONGO_DB_URL)
    white_list = conn.cxautosign.white_list
    exist_user = await white_list.find_one({'qq': user_qq})
    if exist_user == None:
        ids = await white_list.insert_one({'qq': user_qq, 'comment': user_commit})
    else:
        await white_list.update_one({'qq': user_qq}, {'$set': {'comment': user_commit}})
        ids = exist_user['_id']
    await session.send(f'添加成功。\nDatabase ID：{ids}')
    session.finish()

@on_command('list_white_list_user', aliases=('查询验证信息'), permission=nonebot.permission.SUPERUSER)
async def command_list_whitelist_user(session: CommandSession):
    count = session.state['count']
    await session.send(f'正在显示 {count} 条记录：')
    conn = AsyncIOMotorClient(config.MONGO_DB_URL)
    white_list = conn.cxautosign.white_list
    k = 0
    msg_list = []
    async for user in white_list.find():
        k += 1
        msg_list.append(f'QQ： {user["qq"]}\n验证消息：{user["comment"] if not user["comment"] == "" else "无验证"}')
        if k >= count: break
        pass
    msg_list.reverse()
    for msg in msg_list:
        await session.send(msg)
        pass
    session.finish()

@command_list_whitelist_user.args_parser
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    arg_list = arg.split(" ")
    arg = arg_list[1] if len(arg_list) >= 2 else arg_list[0]
    if arg == '':
        session.state['count'] = config.MAX_WHITELIST_DIAPLAY
        pass
    else:
        try:
            h = abs(int(arg))
            h = h if not h == 0 else config.MAX_WHITELIST_DIAPLAY
        except:
            await session.send(f"错误的参数：{arg}")
            session.finish()
            pass
        session.state['count'] = h if h > 0 else 10
        pass
    session.state["args"] = arg
    pass

@on_command('broadcast', aliases=('广播消息'), permission=nonebot.permission.SUPERUSER)
async def command_new_broadcast(session: CommandSession):
    broadcast_msg = session.state['msg']
    await session.send(f"已经收到大小为{len(broadcast_msg)}字的消息，即将在5秒后在所有用户间广播。")
    message_generator = lambda x: f'{broadcast_msg}'
    nonebot.logger.info(f'收到全区广播消息 内容 \n {broadcast_msg}')
    nonebot.scheduler.add_job(broadcast_now, run_date=datetime.datetime.fromtimestamp(time.time()+5), args=[message_generator,])
    session.finish()
    pass

@command_new_broadcast.args_parser
async def _(session: CommandSession):
    if session.state.get("first_run", None) == None:
        await session.send("请输入广播消息。")
        session.state['first_run'] = 'skyrain'
        session.pause()
        pass
    # arg = session.current_arg_text.strip()
    session.state['msg'] = session.current_arg

@on_request('friend')
async def _(session: RequestSession):
    conn = AsyncIOMotorClient(config.MONGO_DB_URL)
    white_list = conn.cxautosign.white_list
    try:
        target = await white_list.find_one({'qq': int(session.ctx['user_id'])})
        if target == None:
            await session.reject('您未在白名单中。')
            return
    except:
        await session.reject('系统错误，或您未在白名单中。')
        return
    if not target['comment'] == '':
        if target['comment'] in session.ctx['comment']:
            await session.approve('验证成功')
        else:
            await session.reject('验证信息不正确。')
            return
    else:
        await session.approve('验证成功')
    nonebot.scheduler.add_job(welcome_new, run_date=datetime.datetime.fromtimestamp(time.time()+2), args=[int(session.ctx['user_id'])])
    pass


@nonebot.scheduler.scheduled_job('cron',year='*', month='*', day='*', week='*', day_of_week='1,2,3,4,5', hour='9,15', minute='10,15,20,25', second=0)
#@nonebot.scheduler.scheduled_job('date', run_date=datetime.datetime.fromtimestamp(time.time()+10))
async def checkTime():
    await sign_v2()
    pass

@nonebot.scheduler.scheduled_job('date', run_date=datetime.datetime.fromtimestamp(time.time()+5))
async def onBootEvent():
    nonebot.logger.info('正在广播系统更新信息')
    generator = lambda user: config.START_BROADCAST_STR
    await broadcast_now(generator)
    pass
