import re
import requests
import asyncio
import json
import httpx

# I love you.--You’ll always be my dearest friend.

# 签到url
# https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/
# preSign?activeId=126433134&classId=19047512&courseId=209403053

# 课程主页url
# http://mooc1-2.chaoxing.com/visit/interaction

# 课程任务url
# https://mobilelearn.chaoxing.com/widget/pcpick/stu/index?courseId=209320132&jclassId=18855085

# 登录URL
# http://i.chaoxing.com/vlogin?passWord=passwordwu&userName=username

# 手势签到验证URL
# https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode?activeId=134706366&signCode=147896325


class AutoSign(object):

    def __init__(self, username, password, schoolid=None, cookies: dict=None):
        self.headers = {
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'}
        self.session = requests.session()
        # Chooseable
        if not cookies == None:
            requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies)
            if self.check_valid():
                return
        self.session.cookies.clear()
        #
        # 登录-手机邮箱登录
        if schoolid:
            r = self.session.post('http://passport2-api.chaoxing.com/v6/idNumberLogin?fid={}&idNumber={}'.format(schoolid, username), data={'pwd': password})
        else:
            r = self.session.post(
                'http://i.chaoxing.com/vlogin?passWord={}&userName={}'.format(password, username), headers=self.headers)

        print(r.text)
        pass

    def get_cookies(self,) -> dict:
        return requests.utils.dict_from_cookiejar(self.session.cookies)

    def check_valid(self,) -> bool:
        "检测cookie是否失效"
        '''
        方法采用请求超星个人主页地址 http://i.chaoxing.com 并检测html特征值
        '''
        return self.session.get("http://i.chaoxing.com/", headers=self.headers).text.find("扫码登录") == -1

    def _get_all_classid(self) -> list:
        '''获取课程主页中所有课程的classid和courseid'''
        re_rule = r'<li style="position:relative">[\s]*<input type="hidden" name="courseId" value="(.*)" />[\s].*<input type="hidden" name="classId" value="(.*)" />[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[s].*[\s]*[\s].*[\s].*[\s].*[\s].*[\s].*<a  href=\'.*\' target="_blank" title=".*">(.*)</a>'
        r = self.session.get(
            'http://mooc1-2.chaoxing.com/visit/interaction',
            headers=self.headers)
        res = re.findall(re_rule, r.text)
        return res

    async def _get_activeid(self, classid, courseid, classname):
        '''访问任务面板获取课程的签到任务id'''
        sign_re_rule = r'<div class="Mct" onclick="activeDetail\((.*),2,null\)">[\s].*[\s].*[\s].*[\s].*<dd class="green">.*</dd>'
        r = self.session.get(
            'https://mobilelearn.chaoxing.com/widget/pcpick/stu/index?courseId={}&jclassId={}'.format(
                courseid, classid), headers=self.headers)
        # Todo 获取到activeid[()]
        res = re.findall(sign_re_rule, r.text)
        if res != []:  # 满足签到条件
            return {
                'classid': classid,
                'courseid': courseid,
                'activeid': res[0],
                'classname': classname}

    def _sign(self, classid, courseid, activeid, checkcode=None):
        '''签到函数'''
        if checkcode is not None:
            '''手势签到'''
            # 手势签到验证URL
            # https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode?activeId=134706366&signCode=147896325
            check_status = self.session.get(
                'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode?activeId={}&signCode={}'.format(
                    activeid, checkcode), headers=self.headers)
            check_status = json.loads(check_status.text)
            if check_status['result'] == '0':
                return '验证码错误'
            r = self.session.get(
                'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/signIn?courseId={}&classId={}&activeId={}'.format(
                    courseid, classid, activeid), headers=self.headers)
            res = re.findall('<title>(.*)</title>', r.text)
            return res[0]

        else:
            r = self.session.get(
                'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/preSign?activeId={}&classId={}&fid=39037&courseId={}'.format(
                    activeid, classid, courseid), headers=self.headers)
            res = re.findall('<title>(.*)</title>', r.text)
            return res[0]

    def run(self, checkcode=None):
        # 获取主页所有课程classid和coureseid
        # 因为具体不知道那一节需要签到，则直接遍历所有课程，都进行签到操作
        classid_courseId = self._get_all_classid()
        tasks = []
        # 获取所有课程签到activeid，虽然遍历了所有课程，但是只会签到一次
        for i in classid_courseId:
            coroutine = self._get_activeid(i[1], i[0], i[2])
            tasks.append(coroutine)
        # loop = asyncio.get_event_loop()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(asyncio.gather(*tasks))
        for d in result:
            if d is not None:
                return '{}:{}'.format(d['classname'], self._sign(
                    d['classid'], d['courseid'], d['activeid'], checkcode))

class AutoSignASync():
    def __init__(self, cookies=None):
        self._should_init = True
        self._p_cookies = cookies
        self.logging = {}
        self.headers = {
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'}
        self.session = httpx.AsyncClient()
        pass

    def get_cookies(self,) -> dict:
        return requests.utils.dict_from_cookiejar(self.session.cookies.jar)

    async def init(self, username, password, schoolid=None):
        if not self._p_cookies == None: 
            self.session.cookies = self._p_cookies
            self._should_init = await self.check_valid()
        if self._should_init: 
            self.logging['login'] = 'Rejected by cookies valid.'
        # 登录-手机邮箱登录
        if schoolid:
            r = await self.session.post('http://passport2-api.chaoxing.com/v6/idNumberLogin?fid={}&idNumber={}'.format(schoolid, username), data={'pwd': password})
        else:
            r = await self.session.post('http://i.chaoxing.com/vlogin?passWord={}&userName={}'.format(password, username), headers=self.headers)
            pass
        self.logging['login'] = r.text
        pass

    async def check_valid(self,) -> bool:
        response = await self.session.get("http://i.chaoxing.com/", headers=self.headers)
        return response.text.find("扫码登录") == -1

    async def _get_all_classid(self) -> list:
        '''获取课程主页中所有课程的classid和courseid'''
        re_rule = r'<li style="position:relative">[\s]*<input type="hidden" name="courseId" value="(.*)" />[\s].*<input type="hidden" name="classId" value="(.*)" />[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[s].*[\s]*[\s].*[\s].*[\s].*[\s].*[\s].*<a  href=\'.*\' target="_blank" title=".*">(.*)</a>'
        r = await self.session.get(
            'http://mooc1-2.chaoxing.com/visit/interaction',
            headers=self.headers)
        res = re.findall(re_rule, r.text)
        self.logging['class_id_re'] = res
        return res

    async def _get_activeid(self, classid, courseid, classname):
        '''访问任务面板获取课程的签到任务id'''
        sign_re_rule = r'<div class="Mct" onclick="activeDetail\((.*),2,null\)">[\s].*[\s].*[\s].*[\s].*<dd class="green">.*</dd>'
        r = await self.session.get(
            'https://mobilelearn.chaoxing.com/widget/pcpick/stu/index?courseId={}&jclassId={}'.format(
                courseid, classid), headers=self.headers)
        # Todo 获取到activeid[()]
        res = re.findall(sign_re_rule, r.text)
        if res != []:  # 满足签到条件
            return {
                'classid': classid,
                'courseid': courseid,
                'activeid': res[0],
                'classname': classname}
    
    async def _sign(self, classid, courseid, activeid, checkcode=None):
        '''签到函数'''
        if checkcode is not None:
            '''手势签到'''
            # 手势签到验证URL
            # https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode?activeId=134706366&signCode=147896325
            check_status = await self.session.get(
                'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode?activeId={}&signCode={}'.format(
                    activeid, checkcode), headers=self.headers)
            check_status = json.loads(check_status.text)
            self.logging[f'sign_{courseid}'] = check_status.text
            if check_status['result'] == '0':
                return '验证码错误'
            r = await self.session.get(
                'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/signIn?courseId={}&classId={}&activeId={}'.format(
                    courseid, classid, activeid), headers=self.headers)
            res = re.findall('<title>(.*)</title>', r.text)
            return res[0]

        else:
            r = await self.session.get(
                'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/preSign?activeId={}&classId={}&fid=39037&courseId={}'.format(
                    activeid, classid, courseid), headers=self.headers)
            res = re.findall('<title>(.*)</title>', r.text)
            self.logging[f'sign_{courseid}'] = r.text
            return res[0]
    
    async def run(self, checkcode=None):
        # 获取主页所有课程classid和coureseid
        # 因为具体不知道那一节需要签到，则直接遍历所有课程，都进行签到操作
        classid_courseId = await self._get_all_classid()
        tasks = []
        # 获取所有课程签到activeid，虽然遍历了所有课程，但是只会签到一次
        for i in classid_courseId:
            coroutine = await self._get_activeid(i[1], i[0], i[2])
            tasks.append(coroutine)
        results = []
        for d in tasks:
            if d is not None:
                results.append( '{}:{}'.format(d['classname'], await self._sign(
                    d['classid'], d['courseid'], d['activeid'], checkcode)))
        return results
    pass

async def testSign():
    c = AutoSignASync()
    await c.init('', '', '')
    k = await c.run()
    print(str(k))
    pass

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(testSign())
    pass
