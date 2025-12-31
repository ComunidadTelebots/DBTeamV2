-- Ported to python_bot/legacy/utils_lua.py
-- See python_bot/legacy for Python equivalents.
    if (#list > 0) then
        return list
    end
    return false
end

function trim(text)
    local chars_tmp = {}
    local chars_m = {}
    local final_str = ""
    local text_arr = {}
    local ok = false
    local i
    for i=1, #text do
        table.insert(chars_tmp, text:sub(i, i))
    end
    i=1
    while(chars_tmp[i]) do
        if tostring(chars_tmp[i]):match('%S') then
            table.insert(chars_m, chars_tmp[i])
            ok = true
        elseif ok == true then
            table.insert(chars_m, chars_tmp[i])
        end
        i=i+1
    end
    i=#chars_m
    ok=false
    while(chars_m[i]) do
        if tostring(chars_m[i]):match('%S') then
            table.insert(text_arr, chars_m[i])
            ok = true
        elseif ok == true then
            table.insert(text_arr, chars_m[i])
        end
        i=i-1
    end
    for i=#text_arr, 1, -1 do
        final_str = final_str..text_arr[i]
    end
    return final_str
end

function underline(text, underline_spaces)
  local chars = {}
  local text_str = ""
  local symbol = trim(" ̲")
  for i=1, #text do
      table.insert(chars, text:sub(i, i))
  end
  for i=1, #chars do
      space = chars[i] == ' '
      if (not space) then
          text_str = text_str..chars[i]..symbol
      elseif (underline_spaces) then
          text_str = text_str..chars[i]..symbol
      else
          text_str = text_str..chars[i]
      end
  end
  return text_str
end

function up_underline(text, underline_spaces)
  local chars = {}
  local text_str = ""
  local symbol = trim(" ̅ ")
  for i=1, #text do
      table.insert(chars, text:sub(i, i))
  end
  for i=1, #chars do
      space = chars[i] == ' '
      if (not space) then
          text_str = text_str..chars[i]..symbol
      elseif (underline_spaces) then
          text_str = text_str..chars[i]..symbol
      else
          text_str = text_str..chars[i]
      end
  end
  return text_str
end

function strike_out(text, underline_spaces)
  local chars = {}
  local text_str = ""
  local symbol = trim(" ̶")
  for i=1, #text do
      table.insert(chars, text:sub(i, i))
  end
  for i=1, #chars do
      space = chars[i] == ' '
      if (not space) then
          text_str = text_str..chars[i]..symbol
      elseif (underline_spaces) then
          text_str = text_str..chars[i]..symbol
      else
          text_str = text_str..chars[i]
      end
  end
  return text_str
end
