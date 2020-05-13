from motor.motor_asyncio import AsyncIOMotorClient
import time
import nonebot
import datetime
import traceback
import random
from . import config
from .config import LATER_TIME, TRY_TIME
from .libcxsign import AutoSignASync

# I mean, especially after your exchange with her yesterday...YOU KIND OF LEFT HER HANGING THIS MORNING,YOU KNOW?

async def perform_config(qq_account: str, username: str, password: str, fid: str=None):
    conn = AsyncIOMotorClient(config.MONGO_DB_URL)
    users = conn.cxautosign.users
    data = {'qq': qq_account, 'username': username, 'password':password, 'fid': fid, 'last_update': int(time.time()), }
    if (i:=await users.find_one({'qq': qq_account})) == None:
        data['create_time'] = data['last_update']
        data['eval_times'] = []
        ids = await users.insert_one(data)
        return ids.inserted_id
    else:
        await users.update_one({'qq': qq_account}, {'$set': data})
        return i['_id']
    pass

async def do_sign():
    conn = AsyncIOMotorClient(config.MONGO_DB_URL)
    users = conn.cxautosign.users
    bot = nonebot.get_bot()
    async for user in users.find():
        eval_data = {'time': int(time.time()), 'result': None, 'logging': None, 'exception': None, 'succ': False}
        try:
            # AutoSign
            autosign = AutoSignASync()
            await autosign.init(user['username'], user['password'], user['fid'])
            result = await autosign.run()
            eval_data['result'] = result
            eval_data['logging'] = autosign.logging
            eval_data['succ'] = (not result == None)
            if not result == None:
                await bot.send_private_msg(user_id=int(user['qq']), message="超星自动签到：\n\n自动签到成功，签到列表\n"+'\n'.join(result))
        except Exception as e:
            eval_data['exception'] = str(e)
            pass
        # Update database
        e_data = user['eval_times']
        e_data.append(eval_data)
        await users.update_one({'qq': user['qq']}, {'$set': {'eval_times': e_data}})
        pass
    pass

async def getEvalData(qq_account: str):
    conn = AsyncIOMotorClient(config.MONGO_DB_URL)
    users = conn.cxautosign.users
    user = await users.find_one({'qq': qq_account})
    return user['eval_times']

async def sign_v2():
    '''
    仅调用一次，但确保每个用户都被成功调用
    '''
    global TRY_TIME
    client = AsyncIOMotorClient(config.MONGO_DB_URL)
    users = client.cxautosign.users
    async for user in users.find():
        # 更新重试次数
        await users.update_one({'qq': user['qq']}, {'$set': {'eval_count': TRY_TIME}})
        result = await sign_v2_single_user(user['qq'], client)
        nonebot.logger.info(f'自动签到： QQ号码{user["qq"]}  状态{"成功" if result[0] else "失败"} 消息{result[1]}')
    pass

async def sign_v2_single_user(qq_account: str, client: AsyncIOMotorClient) -> [bool, str]:
    global LATER_TIME
    global TRY_TIME
    # Using try-except
    bot = nonebot.get_bot()
    try:
        users = client.cxautosign.users
        user = await users.find_one({'qq': qq_account})
        eval_data = {'time': int(time.time()), 'result': None, 'logging': None, 'exception': None, 'succ': False}
        # 更新Evalcount
        eval_count = user['eval_count']
        if eval_count == None or eval_count <= 0:
            await bot.send_private_msg(user_id=int(user['qq']), message=f'超星自动签到插件出现错误：\n重试次数已经达到上限，我们将不再重试，请联系管理员并提供错误报告来解决此问题。\n现在我们建议你手动签到来解决问题。\n抱歉。')
            nonebot.logger.info(f'自动签到： QQ号码{user["qq"]}  状态{"失败"} 消息 重试次数已耗尽')
            eval_data['exception'] = 'end-try-times'
            return [False, 'try_time_max']
        await users.update_one({'qq': user['qq']}, {'$set': {'eval_count': eval_count-1}})
        eval_count -= 1
        await bot.send_private_msg(user_id=int(user['qq']), message=f'超星自动签到插件尝试次数 {eval_count+1}/{TRY_TIME}')
        cookies = user.get('cookies', None)
        autosign = AutoSignASync(cookies=cookies)
        await autosign.init(user['username'], user['password'], user['fid'])
        result = await autosign.run()
        cookies = autosign.get_cookies()
        eval_data['result'] = result
        eval_data['logging'] = autosign.logging
        eval_data['succ'] = (not result == None) and (not result == [])
        if result == None or result == []:
            await bot.send_private_msg(user_id=int(user['qq']), message=f'超星自动签到插件出现错误：\n貌似我们正常执行了签到任务，但是程序显示已经签到的课程为空\n这意味着：\n① 管理员设置的执行时间出现问题\n② 您的账号当前并没有活动中的签到任务\n\n我们会在{LATER_TIME}秒之后重试。如有问题请联系管理员')
            nonebot.scheduler.add_job(sign_v2_single_user, 'date', args=[user['qq'], client], run_date=datetime.datetime.fromtimestamp(time.time()+LATER_TIME))
            return [False, 'none_active_id']
        else:
            result_str = '\n'.join(result)
            await bot.send_private_msg(user_id=int(user['qq']), message=f"超星自动签到插件：\n自动签到成功，签到列表\n{result_str}\n\nDatabase ID: {user['_id']}")
            eval_data['succ'] = True
            return [True, 'success']
    except Exception as e:
        # Error
        if not user == None and 'qq' in user:
            await bot.send_private_msg(user_id=int(user['qq']), message=f'超星自动签到插件出现错误\n我们将在{LATER_TIME}秒之后重试。\n\n调试信息：\nException: {traceback.format_exc()}\nDatabase ID: {user["_id"]}')
            pass
        nonebot.scheduler.add_job(sign_v2_single_user, 'date', args=[user['qq'], client], run_date=datetime.datetime.fromtimestamp(time.time()+LATER_TIME))
        eval_data['exception'] = str(e)
        return [False, f'error {e}']
        pass
    finally:
        if 'cookies' in locals():
            await users.update_one({'qq': user['qq']}, {'$set': {'cookies': cookies}})
        e_data = user['eval_times']
        e_data.append(eval_data)
        await users.update_one({'qq': user['qq']}, {'$set': {'eval_times': e_data}})
    return [True, 'success_end']

async def broadcast_now(message_generator):
    conn = AsyncIOMotorClient(config.MONGO_DB_URL)
    users = conn.cxautosign.users
    bot: nonebot.NoneBot = nonebot.get_bot()
    async for user in users.find():
        # 调用generator生成个性化消息
        try:
            message = message_generator(user)
        except Exception as e:
            nonebot.logger.error(f'QQ号码 {user.get("qq")} 广播消息失败， 详情{str(e)}')
            traceback.print_exception(e)
            continue
        # 发送私信信息
        await bot.send_private_msg(user_id=int(user['qq']), message=message)
        pass
    pass



async def welcome_new(qq_account: str):
    bot = nonebot.get_bot()
    bot.send_private_msg(user_id=int(qq_account), message=f"欢迎使用本机器人，请输入\n命令列表\n来浏览命令。\nCopyright SkyRain 2020")
    pass
