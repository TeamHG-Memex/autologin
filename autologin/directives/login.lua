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

        if splash.args.extra_js then
          assert(splash:runjs(splash.args.extra_js))
          assert(splash:wait(1.0))
        end

        splash:set_viewport_full()
    end

    local entries = splash:history()
    if #entries > 0 then
        local last_response = entries[#entries].response
        return {
            headers=last_response.headers,
            cookies=splash:get_cookies(),
            html=splash:html(),
            http_status=last_response.status,
            page=splash:jpeg{quality=70},
        }
    else
        assert(false, reason)
    end
end
