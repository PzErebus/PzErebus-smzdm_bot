/*
 * Holivator 签到 & 积分兑换 - 青龙 2.x 纯 Node.js 版
 * 
 * 环境变量配置:
 *   holi_username - 用户名 (必填)
 *   holi_password - 密码 (必填)
 *   holi_auto_exchange - 是否自动兑换积分 (可选, 默认 true)
 *   holi_min_points - 最少兑换积分数 (可选, 默认 10)
 */

const BASE_URL = 'https://holivator.de';

const username = process.env.holi_username || '';
const password = process.env.holi_password || '';
const autoExchange = process.env.holi_auto_exchange !== 'false';
const minPoints = parseInt(process.env.holi_min_points || '10', 10);

console.log('[Holivator] 开始, 账号:', username || '未配置');

if (!username || !password) {
    console.log('[Holivator] 错误: 请配置 holi_username 和 holi_password');
    process.exit(1);
}

async function request(url, options = {}) {
    const defaultHeaders = {
        'content-type': 'application/json',
        'accept': 'application/json, text/plain, */*',
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.5 Mobile/15E148 Safari/604.1',
        'origin': BASE_URL,
        'referer': `${BASE_URL}/`
    };
    
    const fetchOptions = {
        method: options.method || 'GET',
        headers: { ...defaultHeaders, ...options.headers },
        body: options.body ? JSON.stringify(options.body) : undefined
    };
    
    const res = await fetch(url, fetchOptions);
    return { 
        status: res.status, 
        body: await res.text(),
        headers: Object.fromEntries(res.headers.entries())
    };
}

async function login() {
    console.log('[Holivator] 开始登录');
    const loginRes = await request(`${BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        body: { username, password },
        headers: { 'referer': `${BASE_URL}/login` }
    });
    
    const loginBody = JSON.parse(loginRes.body);
    const token = loginBody?.data?.access_token;
    
    if (!token) {
        console.log('[Holivator] 登录失败:', loginBody.message || '未知错误');
        process.exit(1);
    }
    console.log('[Holivator] 登录成功');
    return token;
}

async function checkin(token) {
    console.log('[Holivator] 开始签到');
    
    // 尝试多个可能的签到接口
    const endpoints = [
        { path: '/api/v1/user/attendance', method: 'POST' },
        { path: '/api/v1/user/attendance', method: 'GET' },
        { path: '/api/v1/attendance', method: 'POST' },
        { path: '/api/v1/attendance', method: 'GET' }
    ];
    
    for (const { path, method } of endpoints) {
        try {
            const checkRes = await request(`${BASE_URL}${path}`, {
                method: method,
                headers: { 'authorization': `Bearer ${token}` }
            });
            
            const checkBody = JSON.parse(checkRes.body);
            
            if (checkRes.status === 200 || checkRes.status === 201) {
                if (checkBody.code === 0 || checkBody.code === 1 || checkBody.success) {
                    const points = checkBody.data?.points_earned || checkBody.data?.points || '?';
                    console.log(`[Holivator] 签到成功! 获得积分: ${points}`);
                    return true;
                } else if (checkBody.message) {
                    console.log(`[Holivator] 签到结果: ${checkBody.message}`);
                    return true;
                }
            }
        } catch (e) {
            continue;
        }
    }
    
    console.log('[Holivator] 签到失败: 未找到可用的签到接口');
    return false;
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
    
    const infoBody = JSON.parse(infoRes.body);
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
            'referer': `${BASE_URL}/portal/growth`,
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        },
        body: { points }
    });
    
    const result = JSON.parse(exchRes.body);
    
    if (exchRes.status === 200 && result.code === 0) {
        const data = result.data || {};
        console.log(`[Holivator] 兑换成功!`);
        console.log(`[Holivator] 消耗: ${data.points_spent || points} 积分`);
        console.log(`[Holivator] 获得: ${data.exp_gained || '?'} 经验值`);
        console.log(`[Holivator] 当前等级: Lv.${data.new_level || '?'}`);
        return true;
    } else {
        console.log(`[Holivator] 兑换失败: ${result.message || '未知错误'}`);
        return false;
    }
}

async function run() {
    try {
        // 登录
        const token = await login();
        
        // 签到
        await checkin(token);
        
        // 积分兑换
        if (autoExchange) {
            const info = await getPointsInfo(token);
            console.log(`[Holivator] 当前积分: ${info.pointsBalance}, 今日剩余兑换: ${info.remainingToday}`);
            
            const exchangePointsAmount = Math.min(info.pointsBalance, info.remainingToday);
            
            if (exchangePointsAmount >= minPoints) {
                await exchangePoints(token, exchangePointsAmount);
            } else {
                console.log(`[Holivator] 积分不足，跳过兑换 (当前: ${exchangePointsAmount}, 最少: ${minPoints})`);
            }
        } else {
            console.log('[Holivator] 已禁用自动兑换');
        }
        
        console.log('[Holivator] 任务完成');
        
    } catch (err) {
        console.log('[Holivator] 异常:', err.message);
        console.log('[Holivator] 堆栈:', err.stack);
    }
}

run();