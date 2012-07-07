mutiny = {
  channel_log: [],
  seen: '0',

  trim_log: function() {
    /* FIXME: If log has grown too long, play nice and delete some events. */
  },

  render_nick: function(nick, template) {
    var color = '#';
    var avatar = '/_skin/avatar.png';
    var max = 'f'.charCodeAt(0);
    for (var n in [0, 1, 2, 3, 4, 5]) {
      var c = nick[n % nick.length];
      color += String.fromCharCode(max - (c.charCodeAt(0) % 6));
    }
    return template.replace(/_NICK_/g, nick)
                   .replace(/mutiny_style=/g, 'style="background: '+color+';" x=')
                   .replace(/mutiny_avatar=/g, 'src="'+avatar+'" x=')
  },

  render_time: function(iid, template) {
    var dt = new Date(parseInt(iid.substring(0, iid.indexOf('-')))*1000);
    var mm = (' 0'+dt.getMinutes());
    var hh = (' 0'+dt.getHours());
    return template.replace(/_HH_MM_/g,
             hh.substring(hh.length-2) +':'+ mm.substring(mm.length-2));
  },

  render: function(data) {
    for (idx in data) {
      mutiny.channel_log.push(data[idx]);
      var iid = data[idx][0];
      var info = data[idx][1];
      var tpl = $('#template-'+info.event).html();
      var dom_id = iid;
      var target = '#channel';

      if (info.event == 'whois') {
        dom_id = 'whois-'+info.nick;
        target = '#people';
        if (info.userinfo) tpl = tpl.replace(/_INFO_/g, info.userinfo);
      }
      var oi = $('#'+dom_id);
      if (info.event == 'delete') {
        $('#'+info.target).remove();
      }
      else if (tpl) {
        tpl = mutiny.render_time(iid,
                mutiny.render_nick(info.nick, tpl));
        if (info.text) tpl = tpl.replace(/_TEXT_/g,
                                         info.text.replace(/\n/g, '<br>'));
        if (oi.html()) {
          oi.html($(tpl).html());
        } else {
          $(target).append($(tpl).attr('id', dom_id));
        }
      }
      if (iid > mutiny.seen) mutiny.seen = iid;
    }
    mutiny.trim_log();

    /* Don't refresh immediately, humans don't type that fast. */
    setTimeout('mutiny.load_data(60)', 150);
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
