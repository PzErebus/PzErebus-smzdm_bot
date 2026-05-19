/*
 * Holivator 签到 & 积分兑换 - 青龙 2.x 纯 Node.js 版
 * 
 * 环境变量配置:
 *   holi_username - 用户名 (必填)
 *   holi_password - 密码 (必填)
 *   holi_user_agent - 自定义 User-Agent (可选)
 *   holi_auto_exchange - 是否自动兑换积分 (可选, 默认 true)
 *   holi_min_points - 最少兑换积分数 (可选, 默认 10)
 */

const BASE_URL = 'https://holivator.de';

const username = process.env.holi_username || '';
const password = process.env.holi_password || '';
const userAgent = process.env.holi_user_agent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0';
const autoExchange = process.env.holi_auto_exchange !== 'false';
const minPoints = parseInt(process.env.holi_min_points || '10', 10);

const maskString = (str, showLen = 3) => {
    if (!str || str.length <= showLen) return '*'.repeat(str?.length || 3);
    return str.slice(0, showLen) + '*'.repeat(str.length - showLen);
};

const notify = {
    success: (msg) => console.log(`【任务完成】${msg}`),
    fail: (msg) => console.log(`【失败】${msg}`),
    info: (msg) => console.log(`【信息】${msg}`)
};

console.log('[Holivator] 开始执行, 账号:', maskString(username, 4));

if (!username || !password) {
    console.log('[Holivator] 错误: 请配置 holi_username 和 holi_password');
    notify.fail('配置错误: 请配置 holi_username 和 holi_password');
    process.exit(1);
}

const REQUEST_TIMEOUT = 15000;

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function randomDelay() {
    const delayMinutes = Math.floor(Math.random() * 30) + 1;
    const delayMs = delayMinutes * 60 * 1000;
    console.log(`[Holivator] 随机延迟 ${delayMinutes} 分钟开始执行...`);
    await sleep(delayMs);
}

async function shortRandomDelay(baseSeconds = 60) {
    const jitter = Math.floor(Math.random() * 30) + 1;
    const delayMs = (baseSeconds + jitter) * 1000;
    const delayMinutes = (delayMs / 60000).toFixed(1);
    console.log(`[Holivator] 等待 ${delayMinutes} 分钟后继续...`);
    await sleep(delayMs);
}

async function exponentialBackoff(attempt, baseDelay = 60) {
    const expDelay = baseDelay * Math.pow(2, Math.min(attempt, 5));
    const jitter = Math.floor(Math.random() * expDelay * 0.4) - expDelay * 0.2;
    const finalDelay = Math.min(Math.max(expDelay + jitter, baseDelay), 600);
    console.log(`[Holivator] 指数退避等待 ${(finalDelay / 60).toFixed(1)} 分钟 (第 ${attempt} 次重试)`);
    await sleep(finalDelay * 1000);
}

const safeJsonParse = (str, fallback = {}) => {
    if (!str || typeof str !== 'string') return fallback;
    try {
        return JSON.parse(str);
    } catch {
        console.log('[Holivator] JSON解析失败，使用默认值');
        return fallback;
    }
};

async function request(url, options = {}) {
    const defaultHeaders = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'user-agent': userAgent,
        'origin': BASE_URL,
        'referer': `${BASE_URL}/`,
        'sec-ch-ua': '"Chromium";v="148", "Microsoft Edge";v="148", "Not(A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'content-type': 'application/json'
    };

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    const fetchOptions = {
        method: options.method || 'GET',
        headers: { ...defaultHeaders, ...options.headers },
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
        redirect: 'follow'
    };

    try {
        const res = await fetch(url, fetchOptions);
        return {
            status: res.status,
            body: await res.text(),
            headers: Object.fromEntries(res.headers.entries())
        };
    } catch (err) {
        if (err.name === 'AbortError') {
            console.log(`[Holivator] 请求超时: ${url}`);
        } else {
            console.log(`[Holivator] 请求异常: ${err.message}`);
        }
        throw err;
    } finally {
        clearTimeout(timeout);
    }
}

async function login() {
    console.log('[Holivator] 开始登录');
    const loginRes = await request(`${BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        body: { username, password },
        headers: { 'referer': `${BASE_URL}/login` }
    });

    const loginBody = safeJsonParse(loginRes.body);
    const token = loginBody?.data?.access_token;

    if (!token) {
        const errMsg = loginBody.message || '未知错误';
        console.log('[Holivator] 登录失败:', errMsg);
        notify.fail(`登录失败: ${errMsg}`);
        process.exit(1);
    }
    console.log('[Holivator] 登录成功');
    return token;
}

async function checkin(token) {
    console.log('[Holivator] 尝试签到');

    const endpoints = [
        { path: '/api/v1/user/attendance', method: 'POST' },
        { path: '/api/v1/user/attendance', method: 'GET' },
        { path: '/api/v1/attendance', method: 'POST' },
        { path: '/api/v1/attendance', method: 'GET' },
        { path: '/api/user/attendance', method: 'POST' },
        { path: '/api/user/attendance', method: 'GET' }
    ];

    for (const { path, method } of endpoints) {
        try {
            const checkRes = await request(`${BASE_URL}${path}`, {
                method: method,
                headers: { 'authorization': `Bearer ${token}` }
            });

            const checkBody = safeJsonParse(checkRes.body);

            if (checkRes.status === 200 || checkRes.status === 201) {
                if (checkBody.code === 0 || checkBody.code === 1 || checkBody.success) {
                    const points = checkBody.data?.points_earned || checkBody.data?.points || '?';
                    console.log(`[Holivator] 签到成功! 获得积分: ${points}`);
                    return { success: true, points: parseInt(points) || 0 };
                } else if (checkBody.message) {
                    console.log(`[Holivator] 签到结果: ${checkBody.message}`);
                    return { success: true, points: 0 };
                }
            }
        } catch (e) {
            continue;
        }
    }

    console.log('[Holivator] 签到失败: 未找到可用的签到接口');
    return { success: false, points: 0 };
}

async function getPointsInfo(token) {
    console.log('[Holivator] 查询积分信息');
    const infoRes = await request(`${BASE_URL}/api/v1/user/exp/info`, {
        method: 'GET',
        headers: {
            'authorization': `Bearer ${token}`,
            'referer': `${BASE_URL}/portal/growth`
        }
    });

    const infoBody = safeJsonParse(infoRes.body);
    const data = infoBody.data || {};

    return {
        pointsBalance: data.points_balance || 0,
        remainingToday: data.remaining_today !== undefined ? data.remaining_today : 50000
    };
}

async function exchangePoints(token, points) {
    console.log(`[Holivator] 兑换 ${points} 积分`);
    const exchRes = await request(`${BASE_URL}/api/v1/user/exp/exchange`, {
        method: 'POST',
        headers: {
            'authorization': `Bearer ${token}`,
            'referer': `${BASE_URL}/portal/growth`
        },
        body: { points }
    });

    const result = safeJsonParse(exchRes.body);

    if (exchRes.status === 200 && result.code === 0) {
        const data = result.data || {};
        console.log(`[Holivator] 兑换成功!`);
        console.log(`[Holivator] 消耗: ${data.points_spent || points} 积分`);
        console.log(`[Holivator] 获得: ${data.exp_gained || '?'} 经验值`);
        console.log(`[Holivator] 当前等级: Lv.${data.new_level || '?'}`);
        return { success: true, msg: `兑换成功! 消耗 ${data.points_spent || points} 积分, 获得 ${data.exp_gained || '?'} 经验值` };
    } else {
        const errMsg = result.message || '未知错误';
        console.log(`[Holivator] 兑换失败: ${errMsg}`);
        return { success: false, msg: `兑换失败: ${errMsg}` };
    }
}

async function run() {
    const result = {
        checkin: false,
        points: 0,
        exchange: false,
        exchangeMsg: '',
        errors: []
    };

    try {
        await randomDelay();

        const token = await login();

        let checkinResult = await checkin(token);
        let retryCount = 0;
        const maxRetries = 10;

        while (checkinResult.success && checkinResult.points === 0 && retryCount < maxRetries) {
            retryCount++;
            console.log(`[Holivator] 第 ${retryCount} 次重试签到`);
            await exponentialBackoff(retryCount, 60);
            checkinResult = await checkin(token);
        }

        if (!checkinResult.success) {
            console.log('[Holivator] 签到失败，跳过积分兑换');
            result.errors.push('签到失败: 未找到可用的签到接口');
            notify.fail(`Holivator 签到失败: 未找到可用的签到接口`);
            console.log('[Holivator] 任务完成');
            return;
        }

        if (retryCount >= maxRetries && checkinResult.points === 0) {
            console.log('[Holivator] 已达最大重试次数，仍未获得积分');
            result.errors.push('已达最大重试次数，仍未获得积分');
            notify.info(`Holivator 签到成功但未获得积分 (重试${maxRetries}次)`);
            console.log('[Holivator] 任务完成');
            return;
        }

        result.checkin = true;
        result.points = checkinResult.points;

        if (autoExchange) {
            const info = await getPointsInfo(token);
            console.log(`[Holivator] 当前积分: ${info.pointsBalance}, 今日剩余兑换: ${info.remainingToday}`);

            const exchangePointsAmount = Math.min(info.pointsBalance, info.remainingToday);

            if (exchangePointsAmount >= minPoints) {
                await shortRandomDelay(30);
                const exchResult = await exchangePoints(token, exchangePointsAmount);
                if (exchResult.success) {
                    result.exchange = true;
                    result.exchangeMsg = exchResult.msg;
                    notify.success(`Holivator 任务完成!\n签到获得: ${result.points} 积分\n${exchResult.msg}`);
                } else {
                    result.errors.push(exchResult.msg);
                    notify.info(`Holivator 签到成功 (${result.points}积分), 但${exchResult.msg}`);
                }
            } else {
                console.log(`[Holivator] 积分不足，跳过兑换 (当前: ${exchangePointsAmount}, 最少: ${minPoints})`);
                notify.info(`Holivator 签到成功! 获得 ${result.points} 积分, 当前余额 ${exchangePointsAmount} 不足兑换`);
            }
        } else {
            console.log('[Holivator] 已禁用自动兑换');
            notify.success(`Holivator 签到成功! 获得 ${result.points} 积分 (自动兑换已禁用)`);
        }

        console.log('[Holivator] 任务完成');

    } catch (err) {
        console.log('[Holivator] 异常:', err.message);
        result.errors.push(err.message);
        notify.fail(`Holivator 执行异常: ${err.message}`);
    }
}

run();
