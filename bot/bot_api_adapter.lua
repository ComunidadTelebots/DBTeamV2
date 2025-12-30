local json = require('libs.JSON')
local has_https, https = pcall(require, 'ssl.https')
local has_socket, socket_http = pcall(require, 'socket.http')
local ltn12 = require('ltn12')

local BOT_TOKEN = os.getenv('BOT_TOKEN') or ''
if BOT_TOKEN == '' then
  print('BOT_TOKEN not set. Set BOT_TOKEN env var to use Bot API adapter.')
  return
end

local API_BASE = 'https://api.telegram.org/bot' .. BOT_TOKEN

local function http_post(url, body, headers)
  local resp = {}
  local req = { url = url, method = 'POST', source = ltn12.source.string(body or ''), sink = ltn12.sink.table(resp) }
  req.headers = headers or {}
  if not req.headers['Content-Type'] then req.headers['Content-Type'] = 'application/json' end
  if not req.headers['Content-Length'] then req.headers['Content-Length'] = tostring(#(body or '')) end
  if has_https then
    local r, code, h = https.request(req)
    return table.concat(resp), code, h
  elseif has_socket then
    local r, code, h = socket_http.request(req)
    return table.concat(resp), code, h
  else
    return nil, 'no-http'
  end
end

local function bot_api_request(method, payload)
  local url = API_BASE .. '/' .. method
  local body = json:encode(payload or {})
  local resp, code = http_post(url, body, { ['Content-Type'] = 'application/json' })
  if not resp then return nil, code end
  local ok, obj = pcall(json.decode, resp)
  if ok then return obj end
  return nil, resp
end

-- Override tdcli_function to map basic methods to Bot API
-- Override tdcli_function to map common TDLib-like calls to Bot API 9.2 equivalents
tdcli_function = function(call, cb, extra)
  if not call or not call.ID then return end
  local id = call.ID

  local function safe_cb(res)
    if cb then pcall(cb, extra, res) end
    return res
  end

  -- helpers to extract common fields
  local function get_chat_id(c)
    return c.chat_id_ or c.chat_id or (c.chat and c.chat.id) or 0
  end

  local function parse_parse_mode(c)
    if not c or not c.parse_mode_ then return nil end
    local pm = c.parse_mode_.ID or c.parse_mode_
    if pm == 'TextParseModeMarkdown' or pm == 'Markdown' then return 'Markdown' end
    if pm == 'TextParseModeHTML' or pm == 'HTML' then return 'HTML' end
    return nil
  end

  if id == 'SendMessage' then
    local chat_id = get_chat_id(call)
    local text = ''
    if call.input_message_content_ and call.input_message_content_.text_ then text = call.input_message_content_.text_ end
    local parse_mode = parse_parse_mode(call.input_message_content_)
    local payload = { chat_id = chat_id, text = text }
    if parse_mode then payload.parse_mode = parse_mode end
    return safe_cb(bot_api_request('sendMessage', payload))

  elseif id == 'SendPhoto' then
    local chat_id = get_chat_id(call)
    local photo = call.photo_ or (call.input_message_content_ and call.input_message_content_.photo_)
    local caption = call.caption_ or (call.input_message_content_ and call.input_message_content_.caption_)
    local payload = { chat_id = chat_id, photo = photo }
    if caption then payload.caption = caption end
    return safe_cb(bot_api_request('sendPhoto', payload))

  elseif id == 'SendDocument' then
    local chat_id = get_chat_id(call)
    local doc = call.document_ or (call.input_message_content_ and call.input_message_content_.document_)
    local caption = call.caption_ or (call.input_message_content_ and call.input_message_content_.caption_)
    local payload = { chat_id = chat_id, document = doc }
    if caption then payload.caption = caption end
    return safe_cb(bot_api_request('sendDocument', payload))

  elseif id == 'SendAudio' or id == 'SendVoice' then
    local chat_id = get_chat_id(call)
    local audio = call.audio_ or call.voice_ or (call.input_message_content_ and (call.input_message_content_.audio_ or call.input_message_content_.voice_))
    local payload = { chat_id = chat_id }
    if id == 'SendVoice' then payload.voice = audio else payload.audio = audio end
    return safe_cb(bot_api_request(id == 'SendVoice' and 'sendVoice' or 'sendAudio', payload))

  elseif id == 'SendVideo' then
    local chat_id = get_chat_id(call)
    local video = call.video_ or (call.input_message_content_ and call.input_message_content_.video_)
    local caption = call.caption_ or (call.input_message_content_ and call.input_message_content_.caption_)
    local payload = { chat_id = chat_id, video = video }
    if caption then payload.caption = caption end
    return safe_cb(bot_api_request('sendVideo', payload))

  elseif id == 'SendSticker' then
    local chat_id = get_chat_id(call)
    local sticker = call.sticker_ or (call.input_message_content_ and call.input_message_content_.sticker_)
    return safe_cb(bot_api_request('sendSticker', { chat_id = chat_id, sticker = sticker }))

  elseif id == 'SendLocation' then
    local chat_id = get_chat_id(call)
    local loc = call.location_ or (call.input_message_content_ and call.input_message_content_.location_)
    if loc and loc.latitude_ and loc.longitude_ then
      return safe_cb(bot_api_request('sendLocation', { chat_id = chat_id, latitude = loc.latitude_, longitude = loc.longitude_ }))
    end
    return safe_cb({ ok = false, description = 'no-location' })

  elseif id == 'SendMediaGroup' then
    local chat_id = get_chat_id(call)
    local media = call.media_ or call.media_group_ or {}
    return safe_cb(bot_api_request('sendMediaGroup', { chat_id = chat_id, media = media }))

  elseif id == 'EditMessageText' then
    local chat_id = get_chat_id(call)
    local message_id = call.message_id_ or call.message_id
    local text = call.text_ or (call.input_message_content_ and call.input_message_content_.text_)
    local parse_mode = parse_parse_mode(call)
    local payload = {}
    if call.inline_message_id_ then
      payload.inline_message_id = call.inline_message_id_
      payload.text = text
    else
      payload.chat_id = chat_id
      payload.message_id = message_id
      payload.text = text
    end
    if parse_mode then payload.parse_mode = parse_mode end
    return safe_cb(bot_api_request('editMessageText', payload))

  elseif id == 'EditMessageCaption' then
    local chat_id = get_chat_id(call)
    local message_id = call.message_id_ or call.message_id
    local caption = call.caption_ or (call.input_message_content_ and call.input_message_content_.caption_)
    local payload = {}
    if call.inline_message_id_ then
      payload.inline_message_id = call.inline_message_id_
      payload.caption = caption
    else
      payload.chat_id = chat_id
      payload.message_id = message_id
      payload.caption = caption
    end
    return safe_cb(bot_api_request('editMessageCaption', payload))

  elseif id == 'EditMessageReplyMarkup' then
    local chat_id = get_chat_id(call)
    local message_id = call.message_id_ or call.message_id
    local reply_markup = call.reply_markup_
    local payload = {}
    if call.inline_message_id_ then
      payload.inline_message_id = call.inline_message_id_
      payload.reply_markup = reply_markup
    else
      payload.chat_id = chat_id
      payload.message_id = message_id
      payload.reply_markup = reply_markup
    end
    return safe_cb(bot_api_request('editMessageReplyMarkup', payload))

  elseif id == 'DeleteMessages' or id == 'DeleteMessage' then
    local chat_id = get_chat_id(call)
    local message_ids = call.message_ids_ or call.message_id_
    local mid = nil
    if type(message_ids) == 'table' then mid = message_ids[1] end
    if not mid and type(message_ids) == 'number' then mid = message_ids end
    if mid then
      return safe_cb(bot_api_request('deleteMessage', { chat_id = chat_id, message_id = mid }))
    end

  elseif id == 'ForwardMessages' or id == 'ForwardMessage' then
    local from_chat = call.from_chat_id_ or call.from_chat_id
    local to_chat = get_chat_id(call)
    local message_id = call.message_id_ or call.message_id or (call.message_ids_ and call.message_ids_[1])
    if from_chat and message_id then
      return safe_cb(bot_api_request('forwardMessage', { chat_id = to_chat, from_chat_id = from_chat, message_id = message_id }))
    end

  elseif id == 'CopyMessage' then
    local from_chat = call.from_chat_id_ or call.from_chat_id
    local to_chat = get_chat_id(call)
    local message_id = call.message_id_ or call.message_id
    if from_chat and message_id then
      return safe_cb(bot_api_request('copyMessage', { chat_id = to_chat, from_chat_id = from_chat, message_id = message_id }))
    end

  elseif id == 'AnswerCallbackQuery' then
    local callback_id = call.callback_query_id_ or call.callback_query_id
    local text = call.text_
    local show_alert = call.show_alert_
    local payload = { callback_query_id = callback_id }
    if text then payload.text = text end
    if show_alert ~= nil then payload.show_alert = show_alert end
    return safe_cb(bot_api_request('answerCallbackQuery', payload))

  elseif id == 'AnswerInlineQuery' then
    local inline_query_id = call.inline_query_id_ or call.inline_query_id
    local results = call.results_ or {}
    local payload = { inline_query_id = inline_query_id, results = results }
    if call.cache_time_ then payload.cache_time = call.cache_time_ end
    if call.is_personal_ ~= nil then payload.is_personal = call.is_personal_ end
    return safe_cb(bot_api_request('answerInlineQuery', payload))

  elseif id == 'GetMe' then
    return safe_cb(bot_api_request('getMe', {}))

  elseif id == 'GetChat' or id == 'SearchPublicChat' then
    local chat_id = call.chat_id_ or call.username_ or call.chat_id
    if chat_id and type(chat_id) == 'string' and chat_id:sub(1,1) ~= '@' then
      -- leave as-is
    end
    if type(chat_id) == 'string' and chat_id:sub(1,1) ~= '@' and tonumber(chat_id) == nil then
      chat_id = '@' .. chat_id
    end
    return safe_cb(bot_api_request('getChat', { chat_id = chat_id }))

  elseif id == 'GetChatMember' then
    local chat_id = get_chat_id(call)
    local user_id = call.user_id_ or call.user_id
    return safe_cb(bot_api_request('getChatMember', { chat_id = chat_id, user_id = user_id }))

  elseif id == 'GetChatAdministrators' then
    local chat_id = get_chat_id(call)
    return safe_cb(bot_api_request('getChatAdministrators', { chat_id = chat_id }))

  elseif id == 'GetChatMembersCount' or id == 'GetChatMemberCount' then
    local chat_id = get_chat_id(call)
    return safe_cb(bot_api_request('getChatMemberCount', { chat_id = chat_id }))

  elseif id == 'LeaveChat' then
    local chat_id = get_chat_id(call)
    return safe_cb(bot_api_request('leaveChat', { chat_id = chat_id }))

  elseif id == 'BanChatMember' or id == 'KickChatMember' then
    local chat_id = get_chat_id(call)
    local user_id = call.user_id_ or call.user_id
    local until_date = call.until_date_
    local payload = { chat_id = chat_id, user_id = user_id }
    if until_date then payload.until_date = until_date end
    return safe_cb(bot_api_request('banChatMember', payload))

  elseif id == 'UnbanChatMember' then
    local chat_id = get_chat_id(call)
    local user_id = call.user_id_ or call.user_id
    return safe_cb(bot_api_request('unbanChatMember', { chat_id = chat_id, user_id = user_id }))

  elseif id == 'RestrictChatMember' then
    local chat_id = get_chat_id(call)
    local user_id = call.user_id_ or call.user_id
    local permissions = call.permissions_ or call.permissions
    local until_date = call.until_date_
    local payload = { chat_id = chat_id, user_id = user_id, permissions = permissions }
    if until_date then payload.until_date = until_date end
    return safe_cb(bot_api_request('restrictChatMember', payload))

  elseif id == 'PromoteChatMember' then
    local chat_id = get_chat_id(call)
    local user_id = call.user_id_ or call.user_id
    local payload = { chat_id = chat_id, user_id = user_id }
    -- copy promote flags if provided
    for k,v in pairs(call) do if k:match('promote_') then payload[k:gsub('promote_','')] = v end end
    return safe_cb(bot_api_request('promoteChatMember', payload))

  elseif id == 'SendPoll' then
    local chat_id = get_chat_id(call)
    local question = call.question_ or (call.input_message_content_ and call.input_message_content_.question_)
    local options = call.options_ or {}
    return safe_cb(bot_api_request('sendPoll', { chat_id = chat_id, question = question, options = options }))

  elseif id == 'StopPoll' or id == 'StopPoll' then
    local chat_id = get_chat_id(call)
    local message_id = call.message_id_ or call.message_id
    return safe_cb(bot_api_request('stopPoll', { chat_id = chat_id, message_id = message_id }))

  elseif id == 'GetFile' then
    local file_id = call.file_id_ or call.file_id
    return safe_cb(bot_api_request('getFile', { file_id = file_id }))

  elseif id == 'SetWebhook' then
    local url = call.url_ or call.url
    return safe_cb(bot_api_request('setWebhook', { url = url }))

  elseif id == 'DeleteWebhook' then
    return safe_cb(bot_api_request('deleteWebhook', {}))

  else
    -- unsupported / not yet implemented
    return safe_cb({ ok = false, description = 'unsupported-method:' .. tostring(id) })
  end
end

-- Polling loop: getUpdates and forward to tdcli_update_callback
local offset = 0
local function poll()
  while true do
    local ok, res = bot_api_request('getUpdates', { offset = offset, timeout = 20 })
    if ok and ok.result then
      for _, u in ipairs(ok.result) do
        offset = (u.update_id or 0) + 1
        if u.message then
          local msg = u.message
          local data = { ID = 'UpdateNewMessage', message_ = {} }
          local m = data.message_
          m.chat_id_ = msg.chat.id
          m.id_ = msg.message_id
          m.date_ = msg.date
          if msg.from then m.sender_user_id_ = msg.from.id else m.sender_user_id_ = 0 end
          if msg.text then
            m.content_ = { ID = 'MessageText', text_ = msg.text }
          elseif msg.caption then
            m.content_ = { ID = 'MessageText', text_ = msg.caption }
          else
            m.content_ = { ID = 'MessageUnsupported' }
          end
          if msg.reply_to_message then
            m.reply_to_message_id_ = msg.reply_to_message.message_id
          else
            m.reply_to_message_id_ = 0
          end
          tdcli_update_callback(data)

        elseif u.edited_message then
          local msg = u.edited_message
          local data = { ID = 'UpdateMessageEdited', message_ = {} }
          local m = data.message_
          m.chat_id_ = msg.chat.id
          m.id_ = msg.message_id
          m.date_ = msg.edit_date or msg.date
          if msg.from then m.sender_user_id_ = msg.from.id else m.sender_user_id_ = 0 end
          if msg.text then
            m.content_ = { ID = 'MessageText', text_ = msg.text }
          elseif msg.caption then
            m.content_ = { ID = 'MessageText', text_ = msg.caption }
          else
            m.content_ = { ID = 'MessageUnsupported' }
          end
          tdcli_update_callback(data)

        elseif u.callback_query then
          local cq = u.callback_query
          local data = { ID = 'UpdateNewCallbackQuery', callback_query_ = {} }
          local c = data.callback_query_
          c.id_ = cq.id
          c.from_ = cq.from and cq.from.id or 0
          c.data_ = cq.data
          c.inline_message_id_ = cq.inline_message_id
          if cq.message then
            c.message_ = { chat_id_ = cq.message.chat.id, id_ = cq.message.message_id }
          end
          tdcli_update_callback(data)

        elseif u.inline_query then
          local iq = u.inline_query
          local data = { ID = 'UpdateNewInlineQuery', inline_query_ = {} }
          local q = data.inline_query_
          q.id_ = iq.id
          q.from_ = iq.from and iq.from.id or 0
          q.query_ = iq.query
          q.offset_ = iq.offset
          tdcli_update_callback(data)

        elseif u.channel_post then
          local msg = u.channel_post
          local data = { ID = 'UpdateNewChannelMessage', message_ = {} }
          local m = data.message_
          m.chat_id_ = msg.chat.id
          m.id_ = msg.message_id
          m.date_ = msg.date
          if msg.text then
            m.content_ = { ID = 'MessageText', text_ = msg.text }
          elseif msg.caption then
            m.content_ = { ID = 'MessageText', text_ = msg.caption }
          else
            m.content_ = { ID = 'MessageUnsupported' }
          end
          tdcli_update_callback(data)
        end
      end
    else
      -- wait before retry
      os.execute('sleep 1')
    end
  end
end

print('Starting Bot API adapter polling loop (BOT_TOKEN set).')
poll()
