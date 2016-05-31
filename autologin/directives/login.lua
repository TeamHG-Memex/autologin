function main(splash)
    local full_render = splash.args.full_render
    local first_request = true
    splash:on_request(function(request)
        if first_request then
            request:set_timeout(60)
            first_request = false
        end
    end)
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

        if full_render then
            splash:set_viewport_full()
        end
    end

    local entries = splash:history()
    if #entries > 0 then
        local last_response = entries[#entries].response
        local result = {
            headers=last_response.headers,
            cookies=splash:get_cookies(),
            html=splash:html(),
            http_status=last_response.status,
            page=splash:jpeg{quality=80},
        }
        if full_render then
            result.forms = render_elements(splash, 'form')
            result.images = render_elements(splash, 'img')
        end
        return result
    else
        error(reason)
    end
end


function render_elements(splash, tag)
    -- Return a table with base64-encoded screenshots of tag-elements on the page.
    -- Ordering of getElementsByTagName is guaranteed by
    -- https://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#method-getElementsByTagName
    local get_bboxes = splash:jsfunc([[
    function(tag) {
      var elements = document.getElementsByTagName(tag);
      var bboxes = [];
      for (var i = 0; i < elements.length; i++) {
        var r = elements[i].getBoundingClientRect();
        bboxes.push([r.left, r.top, r.right, r.bottom]);
      }
      return bboxes;
    }
    ]])
    local bboxes = get_bboxes(tag)
    local result = {}
    for i = 1, #bboxes do
        local bbox = bboxes[i]
        result[i] = {
            region=bbox,
            screenshot=splash:jpeg{region=bbox, quality=70},
        }
    end
    return result
end
