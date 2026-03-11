const https = require('https');

const BEEHIIV_API_KEY = '3m918WuAZOWqfhwsQRnJeHARxJXw9SMj2X2ojh5Gkyqjzh8VjCj3G2ELcXgdetou';
const BEEHIIV_PUB_ID = 'pub_5c073637-5289-41d7-a0a5-ba03caec7bef';

exports.handler = async (event) => {
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    let email;

    // Netlify form webhook payload is JSON with a `data` object
    try {
        const body = JSON.parse(event.body);
        // Netlify webhook format: { data: { email: '...' }, ... }
        email = (body.data && body.data.email) || body.email;
    } catch (e) {
        // Fallback: form-urlencoded (direct form POST)
        const params = new URLSearchParams(event.body);
        email = params.get('email');
    }

    if (!email) {
        console.error('No email found in payload:', event.body);
        return { statusCode: 400, body: 'Missing email' };
    }

    const payload = JSON.stringify({
        email,
        reactivate_existing: false,
        send_welcome_email: true,
        utm_source: 'website',
        utm_medium: 'organic',
        utm_campaign: 'free-preset',
    });

    return new Promise((resolve) => {
        const options = {
            hostname: 'api.beehiiv.com',
            path: `/v2/publications/${BEEHIIV_PUB_ID}/subscriptions`,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${BEEHIIV_API_KEY}`,
                'Content-Length': Buffer.byteLength(payload),
            },
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                console.log(`Beehiiv response [${res.statusCode}]:`, data);
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    resolve({ statusCode: 200, body: JSON.stringify({ success: true, email }) });
                } else {
                    resolve({ statusCode: res.statusCode, body: data });
                }
            });
        });

        req.on('error', (err) => {
            console.error('Beehiiv API error:', err);
            resolve({ statusCode: 500, body: 'Internal server error' });
        });

        req.write(payload);
        req.end();
    });
};
