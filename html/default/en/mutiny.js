function Mutiny(mutiny_host, mutiny_network, mutiny_channel, global) {
  var dom = null;
  var mutiny = {
    channel_log: [],
    avatars: {},
    seen: '0',
    dom: dom,

    api_url: '',
    retry: 1,
    max_retry: 64,
    max_retry_timeout: 8,
    refresh: 90,
    running: 0,

    trim_log: function() {
      /* FIXME: If log has grown too long, play nice and delete some events. */
    },

    render_text: function(re, data, template) {
      if (data) {
        /* FIXME: Find URLs etc? */
        return template.replace(re, data.replace(/&/g, '&amp;')
                                        .replace(/"/g, '&quot;')
                                        .replace(/'/g, '&#39;')
                                        .replace(/</g, '&lt;')
                                        .replace(/>/g, '&gt;')
                .replace(/([A-Za-z0-9_-]+)\*(\s+)/g,
                         '<a href="javascript:mutiny.click_tag(\'$1\')">$1</a>$2')
                .replace(/(^|\s+)\(([A-Za-z0-9_-]+\*\s+)*[A-Za-z0-9_-]+\*\)/g, '')
  .replace(/(^|\s+)((?:https?:\/\/|www\.)(?:[\w]+\.)(?:\.?[\w]{2,})+(?:\/[^\s\)\>]*)?)/g,
                                          '$1<a target=_blank href=\'$2\'>$2</a>')
             .replace(/(<a target=_blank href=\')(?!(?:http|java))/g, '$1http://')
                                        .replace('/\n/g', '\n<br>'));
      }
      else
        return template;
    },

    render_nick: function(nick, uid, template) {
      var color = '#';
      var avatar = mutiny.avatars[uid];
      var max = 'f'.charCodeAt(0);
      if (nick)
        for (var n in [0, 1, 2, 3, 4, 5]) {
          var c = nick[n % nick.length];
          color += String.fromCharCode(max - (c.charCodeAt(0) % 6));
        }
      else
        color = '#aaa'
      return mutiny.render_text(/_NICK_/g, nick,
               template.replace(/mutiny_style=/g, 'style="background: '+color+';" x=')
                       .replace(/mutiny_avatar=/g, 'src="'+avatar+'" x='))
    },

    render_time: function(iid, template) {
      var dt = new Date(parseInt(iid.substring(0, iid.indexOf('-')))*1000);
      var mm = (' 0'+dt.getMinutes());
      var hh = (' 0'+dt.getHours());
      return template.replace(/_HH_MM_/g,
               hh.substring(hh.length-2) +':'+ mm.substring(mm.length-2));
    },

    render: function(data) {
      /* Schedule refresh first, in case we crash and burn.
       * Introduce some jitter to spread load a bit. */
      var refresh = Math.round((0.5 + Math.random()) * mutiny.refresh);
      setTimeout(global+'.load_data('+refresh+');', Math.random() * 100);

      var muids = mutiny.get_cookie('muid-'+mutiny_network);
      var muid = null;
      var log_id = null;
      if (muids) {
        muids = muids.split(',');
        muid = muids[0];
        log_id = muids[1];
      }

      for (idx in data) {
        mutiny.channel_log.push(data[idx]);
        var iid = data[idx][0];
        var info = data[idx][1];
        var tpl = dom.find('#template-'+info.event).html();
        var dom_id = iid;
        var target = 'channel';

        if (info.update) {
          dom_id = info.update;
        }
        if (info.event == 'whois') {
          dom_id = info.uid;
          if (info.uid == log_id) {
            target = 'me';
          }
          else {
            target = 'people';
          }
          mutiny.avatars[info.uid] = info.avatar;
          var in_channel = (info.channels.indexOf(mutiny_channel) >= 0);
          tpl = mutiny.render_text(/_INFO_/g, info.userinfo,
                   tpl.replace(/_URL_/g, info.url || '')
                      .replace(/_HERE_/g, in_channel ? 'here' : 'gone'));
        }
        var oi = dom.find('#'+dom_id);
        if (info.event == 'delete') {
          dom.find('#'+info.target).remove();
        }
        else if (tpl) {
          tpl = mutiny.render_time(dom_id,
                  mutiny.render_nick(info.nick || '', info.uid || '',
                    mutiny.render_text(/_UID_/g, info.uid,
                      mutiny.render_text(/_STAT_/g, info.stat,
                        mutiny.render_text(/_TEXT_/g, info.text, tpl)))));
          if (oi.html() && (info.event != 'whois')) {
            oi.html(tpl);
            mutiny.apply_filters(oi.children());
          }
          else {
            oi.remove();
            var td = document.getElementById(target);
            var scroll = (td.scrollHeight - td.scrollTop == mutiny.scroll_diff);
            var jqObj = $('<span class="wrap"/>').html(tpl).attr('id', dom_id);
            if (info.event == 'whois') {
              dom.find('#'+target).prepend(jqObj);
            }
            else {
              dom.find('#'+target).append(jqObj);
            }
            if (target == 'channel') {
              mutiny.apply_filters(jqObj.children());
              if (scroll || !mutiny.scroll_diff) {
                td.scrollTop = td.scrollHeight;
                mutiny.scroll_diff = (td.scrollHeight - td.scrollTop);
              }
            }
          }
        }
        if (iid > mutiny.seen) mutiny.seen = iid;
      }

      if (muids) {
        if (mutiny.avatars[log_id]) {
          dom.find('#loginpending, #pleaselogin').hide();
          dom.find('#input, #presence').show();
        }
        else {
          dom.find('#input, #presence, #pleaselogin').hide();
          dom.find('#loginpending').show();
        }
      }
      else {
        dom.find('#loginpending, #presence, #input').hide();
        dom.find('#pleaselogin').show();
      }

      mutiny.trim_log();
    },

    get_cookie: function(name) {
      /* Adapted from http://www.quirksmode.org/js/cookies.html */
      var nameEQ = name + "=";
      var ca = document.cookie.split(';');
      for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
          c = c.substring(1, c.length);
        }
        if (c.indexOf(nameEQ) == 0) {
          return c.substring(nameEQ.length, c.length);
        }
      }
      return null;
    },

    load_data: function(timeout) {
      if (mutiny.running > 0) return;
      mutiny.running += 1;
      $.ajax({
        url: mutiny.api_url,
        timeout: (timeout+10) * 1000,
        dataType: 'json',
        data: {
          'a': 'log',
          'seen': mutiny.seen,
          'timeout': timeout
        },
        success: function(data) {
          mutiny.running -= 1;
          mutiny.retry = 1;
          mutiny.render(data);
          dom.find('#disconnected').hide();
        },
        error: function(jqXHR, stat, errThrown) {
          mutiny.running -= 1;
          setTimeout(global+'.load_data(0);', 1000 * mutiny.retry);
          if (mutiny.retry > 2) {
            for (var i = 1; i <= mutiny.retry; i++) {
              setTimeout('$("#countdown").html('+i+');',
                         1000 * (mutiny.retry-i));
            }
            setTimeout('$("#disconnected").hide();',
                       (1000 * mutiny.retry) - 250);
            $('#disconnected').show();
          }
          if (stat == 'timeout') {
            mutiny.retry = mutiny.retry + 1;
            if (mutiny.retry > mutiny.max_retry_timeout) {
              mutiny.retry = mutiny.max_retry_timeout;
            }
          }
          else {
            if (errThrown) {
              mutiny.retry = mutiny.retry * 2;
              $('#debug_log').prepend($('<p/>').html('Error: '+stat+' '+errThrown));
            }
            if (mutiny.retry > mutiny.max_retry) {
              mutiny.retry = mutiny.max_retry;
            }
          }
        }
      });
    },

    apply_filters: function(jqObj) {
      var filter = dom.find('input[name=filter]:checked').val();
      $(jqObj).show();
      if (filter == 'talk') {
        $(jqObj).filter('.part').hide();
        $(jqObj).filter('.join').hide();
        $(jqObj).filter('.nick').hide();
        $(jqObj).filter('.quit').hide();
      }
      else if (filter == 'voice') {
        $(jqObj).filter(':not(.voice)').hide();
      }
      else if (filter == 'notes') {
        $(jqObj).filter(':not(.notes)').hide();
      }
    },

    filter_all: function() {
      setTimeout(global+".apply_filters("+global+".dom.find('.mutiny_log'));", 10);
    },

    toggle_filter: function(e) {
      $(e.target).children('input[name=filter]').click();
    },

    say: function() {
      var input = dom.find('form#input .privmsg');
      var message = input.attr('value');

      dom.find('form#input').removeClass('error').addClass('sending');
      $.ajax({
        url: mutiny.api_url,
        timeout: 10 * 1000,
        dataType: 'json',
        type: 'POST',
        data: {
          'a': 'say',
          'msg': message,
        },
        success: function(data) {
          dom.find('form#input').removeClass('error').removeClass('sending');
        },
        error: function(jqXHR, stat, errThrown) {
          alert('Oops, sending failed!');
          input.attr('value', message + ' ' + input.attr('value'));
          dom.find('form#input').addClass('error').removeClass('sending');
        }
      });

      input.attr('value', '');
      return false;
    },

    logout: function() {
      $.ajax({
        url: mutiny.api_url,
        timeout: 10 * 1000,
        dataType: 'json',
        type: 'POST',
        data: {
          'a': 'logout',
        },
        success: function(data) {
          mutiny.render([]);
        },
        error: function(jqXHR, stat, errThrown) {
          mutiny.render([]);
        }
      });
    },

    main: function(my_dom) {
      mutiny.dom = dom = my_dom;
      dom.find('form#input').submit(mutiny.say);
      dom.find('p.toggle').click(mutiny.toggle_filter);
      dom.find('#logout').click(mutiny.logout);
      dom.find('input[name=filter]').click(mutiny.filter_all);
      mutiny.api_url = (mutiny_host+'/_api/v1/'+mutiny_network+'/'+mutiny_channel
                        ).replace(/#/g, '');
      mutiny.load_data(0);
    }
  };
  return mutiny;
};
