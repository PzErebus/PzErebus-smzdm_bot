/*
 * Holivator 签到 - 青龙 2.x 纯 Node.js 版
 */

const BASE_URL = 'https://holivator.de';

const username = process.env.holi_username || '';
const password = process.env.holi_password || '';

console.log('[Holivator] 开始, 账号:', username || '未配置');

if (!username || !password) {
    console.log('[Holivator] 错误: 请配置 holi_username 和 holi_password');
    process.exit(1);
}

async function request(url, options = {}) {
    const defaultHeaders = {
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

async function run() {
    try {
        // 登录
        const loginRes = await request(`${BASE_URL}/api/v1/auth/login`, {
            method: 'POST',
            body: { username, password }
        });
        
        console.log('[Holivator] 登录响应状态:', loginRes.status);
        
        const loginBody = JSON.parse(loginRes.body);
        const token = loginBody?.data?.access_token || loginBody?.access_token;
        
        if (!token) {
            console.log('[Holivator] 登录失败:', loginBody.message || '未知错误');
            console.log('[Holivator] 登录响应:', loginRes.body);
            process.exit(1);
        }
        console.log('[Holivator] 登录成功');
        console.log('[Holivator] Token获取成功');

        // 尝试不同的签到接口路径
        const possibleEndpoints = [
            '/api/v1/user/attendance',
            '/api/v1/attendance',
            '/api/user/attendance',
            '/api/attendance',
            '/attendance'
        ];
        
        let success = false;
        for (const endpoint of possibleEndpoints) {
            const checkRes = await request(`${BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'authorization': `Bearer ${token}` }
            });
            
            console.log(`[Holivator] 尝试 ${endpoint} - 状态: ${checkRes.status}`);
            
            try {
                const checkBody = JSON.parse(checkRes.body);
                
                if (checkRes.status === 200 || checkRes.status === 201) {
                    if (checkBody.code === 0 || checkBody.code === 1 || checkBody.success) {
                        console.log('[Holivator] 签到成功!');
                        console.log('[Holivator] 响应:', JSON.stringify(checkBody, null, 2));
                        success = true;
                        break;
                    } else if (checkBody.message) {
                        console.log(`[Holivator] ${endpoint} - 结果: ${checkBody.message}`);
                    }
                }
            } catch (e) {
                console.log(`[Holivator] ${endpoint} - 非JSON响应:`, checkRes.body.substring(0, 100));
            }
        }
        
        if (!success) {
            console.log('[Holivator] 所有接口尝试失败，可能需要手动抓包更新接口地址');
        }
        
    } catch (err) {
        console.log('[Holivator] 异常:', err.message);
        console.log('[Holivator] 堆栈:', err.stack);
    }
}

run();