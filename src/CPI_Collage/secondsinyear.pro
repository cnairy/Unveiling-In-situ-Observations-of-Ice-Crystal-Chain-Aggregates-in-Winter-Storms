function secondsinyear, year, month, day, hour, minute, second
   return, (julday(month, day, year) - julday(1, 1, year) + 1) $
      * 86400 + hour * 3600 + minute * 60 + second
end

