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
        return {
            headers=last_response.headers,
            cookies=splash:get_cookies(),
            html=splash:html(),
            http_status=last_response.status,
            forms=full_render and render_forms(splash) or nil,
            page=splash:jpeg{quality=80},
        }
    else
        assert(false, reason)
    end
end


function render_forms(splash)
  -- Return a table with base64-encoded screenshots of forms on the page.
  -- Ordering of getElementsByTagName is guaranteed by
  -- https://www.w3.org/TR/REC-DOM-Level-1/level-one-core.html#method-getElementsByTagName
  local get_forms_bboxes = splash:jsfunc([[
    function() {
      var forms = document.getElementsByTagName('form');
      var bboxes = [];
      for (var i = 0; i < forms.length; i++) {
        var r = forms[i].getBoundingClientRect();
        bboxes.push([r.left, r.top, r.right, r.bottom]);
      }
      return bboxes;
    }
  ]])
  local bboxes = get_forms_bboxes()
  local forms = {}
  for i = 1, #bboxes do
    forms[i] = {
        region=bboxes[i],
        screenshot=splash:jpeg{region=bboxes[i], quality=70},
    }
  end
  return forms
end
