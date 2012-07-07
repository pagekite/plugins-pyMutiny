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
    return template.replace('_NICK_', nick)
                   .replace('mutiny_style=', 'style="background: '+color+';" x=')
                   .replace('mutiny_avatar=', 'src="'+avatar+'" x=')
  },

  render_time: function(iid, template) {
    var dt = new Date(parseInt(iid.substring(0, iid.indexOf('-')))*1000);
    var mm = (' 0'+dt.getMinutes());
    var hh = (' 0'+dt.getHours());
    return template.replace('_HH_MM_',
             hh.substring(hh.length-2) +':'+ mm.substring(mm.length-2));
  },

  render: function(data) {
    for (idx in data) {
      mutiny.channel_log.push(data[idx]);
      var iid = data[idx][0];
      var info = data[idx][1];
      var tpl = $('#template-'+info.event).html();
      if (tpl) {
        tpl = mutiny.render_time(iid,
                mutiny.render_nick(info.nick, tpl));
        if (info.event == 'whois') {
          $('#whois-'+info.nick).remove();
          if (info.userinfo)
            tpl = tpl.replace('_INFO_', info.userinfo);
          $('#people').append($(tpl).attr('id', 'whois-'+info.nick));
        }
        else {
          $('#'+iid).remove();
          if (info.text)
            tpl = tpl.replace('_TEXT_', info.text);
          $('#channel').append($(tpl).attr('id', iid));
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
                   ).replace('#', '');
    $.getJSON(api_url, {
      'a': 'log',
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
