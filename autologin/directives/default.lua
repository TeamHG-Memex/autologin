function main(splash)
    splash:init_cookies(splash.args.cookies)
    local ok, reason = splash:go{
        splash.args.url,
        headers=splash.args.headers,
        http_method=splash.args.http_method,
        body=splash.args.body,
    }
    if ok then
        assert(splash:wait(0.5))
    end

    local entries = splash:history()
    if #entries > 0 then
        local last_response = entries[#entries].response
        return {
            headers=last_response.headers,
            cookies=splash:get_cookies(),
            html=splash:html(),
            http_status=last_response.status,
        }
    else
        assert(false, reason)
    end
end
