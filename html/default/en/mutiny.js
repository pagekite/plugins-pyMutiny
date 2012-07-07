mutiny = {
  channel_log: [],
  seen: '0',

  trim_log: function() {
    /* FIXME: If log has grown too long, play nice and delete some events. */
  },

  render_nick: function(template, nick) {
    var color = '#';
    var avatar = '/_skin/avatar.png';
    var max = 'f'.charCodeAt(0);
    for (var n in nick) {
      color += String.fromCharCode(max - (nick[n].charCodeAt(0) % 6));
      if (color.length > 6) break;
    }
    return template.replace('_NICK_', nick)
                   .replace('mutiny_style=', 'style="background: '+color+';" x=')
                   .replace('mutiny_avatar=', 'src="'+avatar+'" x=')
  },

  render: function(data) {
    for (idx in data) {
      mutiny.channel_log.push(data[idx]);
      var iid = data[idx][0];
      var info = data[idx][1];
      var tpl = mutiny.render_nick($('#template-'+info.event).html(), info.nick);
      if (tpl) {
        if (info.text)
          tpl = tpl.replace('_TEXT_', info.text);
        $('#channel').append($(tpl).attr('id', iid));
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
