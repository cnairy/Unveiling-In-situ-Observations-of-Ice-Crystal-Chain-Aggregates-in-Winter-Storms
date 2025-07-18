function validatetime, starttime
   z = string(strtrim(0, 2))
   slen = strlen(starttime)
   if slen lt 1 then return, -1
   if slen eq 1 then $
      starttime = z + starttime
   if strpos(starttime, ":") ne -1 then begin
      parts = str_sep(starttime, ':', /trim)
      starttime = ""
      for i = 0, n_elements(parts)-1 do begin
         starttime = starttime + parts[i]
      endfor
   endif
   slen = strlen(starttime)
   for i = 0, slen[0]-1 do begin
      save = strmid(starttime, i, 1)
      if save lt 0 or save gt 9 then $
         return, -1
   endfor
   for i = slen[0], 8 do begin
      starttime = string(starttime, 0)
   endfor
   hour = strmid(starttime, 0, 2)
   min = strmid(starttime, 2, 2)
   sec = strmid(starttime, 4, 2)
   msec = strmid(starttime, 6, 3)
   hourn = strtrim(fix(hour[0]), 2)
   minn = strtrim(fix(min[0]), 2)
   secn = strtrim(fix(sec[0]), 2)
   msecn = strtrim(fix(msec[0]), 2)
   if hourn gt 23 then hourn = 23
   if minn gt 59 then minn = 59
   if secn gt 59 then secn = 59 
   hour = string(hourn)
   min = string(minn)
   sec = string(secn)
   msec = string(msecn)
   if hourn lt 10 then hour = z + hour
   if minn lt 10 then min = z + min
   if secn lt 10 then sec = z + sec
   if msecn lt 100 then msec = z + msec $
      else if msecn lt 10 then msec = z + z + msec
   starttime = hour + ":" + min + ":" + sec + "." + msec
print, starttime
   return, 0
end
