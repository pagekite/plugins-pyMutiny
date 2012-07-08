mutiny = {
  channel_log: [],
  seen: '0',

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
    var avatar = '/_skin/avatar_'+uid[uid.length-1]+'.jpg';
    var max = 'f'.charCodeAt(0);
    for (var n in [0, 1, 2, 3, 4, 5]) {
      var c = nick[n % nick.length];
      color += String.fromCharCode(max - (c.charCodeAt(0) % 6));
    }
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
    /* Schedule refresh first, in case we crash and burn. */
    setTimeout('mutiny.load_data(60)', 50);

    for (idx in data) {
      mutiny.channel_log.push(data[idx]);
      var iid = data[idx][0];
      var info = data[idx][1];
      var tpl = $('#template-'+info.event).html();
      var dom_id = iid;
      var target = 'channel';

      if (info.update) {
        iid = dom_id = info.update;
      }
      if (info.event == 'whois') {
        iid = dom_id = info.uid;
        target = 'people';
        tpl = mutiny.render_text(/_INFO_/g, info.userinfo, tpl);
      }
      var oi = $('#'+dom_id);
      if (info.event == 'delete') {
        $('#'+info.target).remove();
      }
      else if (tpl) {
        tpl = mutiny.render_time(iid,
                mutiny.render_nick(info.nick, info.uid,
                  mutiny.render_text(/_UID_/g, info.uid,
                    mutiny.render_text(/_STAT_/g, info.stat,
                      mutiny.render_text(/_TEXT_/g, info.text, tpl)))));
        if (oi.html()) {
          oi.html($(tpl).html());
        } else {
          var td = document.getElementById(target);
          var scroll = (td.scrollHeight - td.scrollTop == mutiny.scroll_diff);
          $('#'+target).append($(tpl).attr('id', dom_id));
          if (target == 'channel') {
            if (scroll || !mutiny.scroll_diff) {
              td.scrollTop = td.scrollHeight;
              mutiny.scroll_diff = (td.scrollHeight - td.scrollTop);
            }
          }
        }
      }
      if (iid > mutiny.seen) mutiny.seen = iid;
    }
    mutiny.trim_log();
  },

  load_data: function(timeout) {
    var api_url = (mutiny_host+'/_api/v1/'+mutiny_network+'/'+mutiny_channel
                   ).replace(/#/g, '');
    $.getJSON(api_url, {
      'a': 'log',
      'uid': mutiny_uid,
      'seen': mutiny.seen,
      'timeout': timeout
    }, function(data, textStatus, jqXHR) {
      mutiny.render(data);
    });
  },

  main: function() {
    mutiny.load_data(0);
  }
};