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
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'accept': 'application/json, text/plain, */*',
        'origin': BASE_URL,
        'referer': `${BASE_URL}/`
    };
    
    const fetchOptions = {
        method: options.method || 'GET',
        headers: { ...defaultHeaders, ...options.headers },
        body: options.body ? JSON.stringify(options.body) : undefined,
        credentials: 'include'
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

        // 尝试不同的签到接口路径和方法
        const possibleEndpoints = [
            { path: '/api/v1/user/attendance', method: 'POST' },
            { path: '/api/v1/user/attendance', method: 'GET' },
            { path: '/api/v1/attendance', method: 'POST' },
            { path: '/api/v1/attendance', method: 'GET' },
            { path: '/api/user/attendance', method: 'POST' },
            { path: '/api/user/attendance', method: 'GET' },
            { path: '/api/attendance', method: 'POST' },
            { path: '/api/attendance', method: 'GET' },
            { path: '/api/v1/checkin', method: 'POST' },
            { path: '/api/v1/checkin', method: 'GET' },
            { path: '/checkin', method: 'POST' },
            { path: '/user/attendance', method: 'POST' },
            { path: '/attendance', method: 'POST' },
            { path: '/attendance', method: 'GET' }
        ];
        
        let success = false;
        for (const { path, method } of possibleEndpoints) {
            const checkRes = await request(`${BASE_URL}${path}`, {
                method: method,
                headers: { 'authorization': `Bearer ${token}` }
            });
            
            console.log(`[Holivator] 尝试 ${method} ${path} - 状态: ${checkRes.status}`);
            
            try {
                const checkBody = JSON.parse(checkRes.body);
                
                if (checkRes.status === 200 || checkRes.status === 201) {
                    if (checkBody.code === 0 || checkBody.code === 1 || checkBody.success || 
                        (checkBody.message && !checkBody.message.includes('Not Found'))) {
                        console.log('[Holivator] 签到成功!');
                        console.log('[Holivator] 响应:', JSON.stringify(checkBody, null, 2));
                        success = true;
                        break;
                    } else if (checkBody.message) {
                        console.log(`[Holivator] ${method} ${path} - 结果: ${checkBody.message}`);
                    }
                } else if (checkRes.status === 401) {
                    console.log(`[Holivator] ${method} ${path} - 未授权，请检查Token`);
                }
            } catch (e) {
                console.log(`[Holivator] ${method} ${path} - 非JSON响应:`, checkRes.body.substring(0, 150));
            }
        }
        
        if (!success) {
            console.log('[Holivator] 所有接口尝试失败');
            console.log('[Holivator] 请手动抓包获取最新的签到接口地址');
            console.log('[Holivator] 步骤: 1. 打开浏览器开发者工具 2. 登录Holivator 3. 点击签到 4. 查看Network请求');
        }
        
    } catch (err) {
        console.log('[Holivator] 异常:', err.message);
        console.log('[Holivator] 堆栈:', err.stack);
    }
}

run();