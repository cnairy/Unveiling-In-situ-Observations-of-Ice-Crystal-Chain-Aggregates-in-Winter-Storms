PRO cpi_imagedump, fn, jailbars=jailbars, res=res, rate=rate, numcolumns=numcolumns,$
      xpanelsize=xpanelsize, ypanelsize=ypanelsize, project=project, pack=pack, outdir=outdir,$
      naming_convention=naming_convention, hourly=hourly, version=version
   ;PRO to dump a series of roi files to png images, one per minute (or hour)
   ;AB 7/2020
   ;Input:
   ;  fn: roi filenames (use file_search('*.roi'))
   ;  res:  probe resolution for scale bar
   ;  numcolumns:  columns per image, use 4 (default) for 5-second images, 10? for 1Hz
   ;  xpanelsize/ypanelsize:  Each subpanel size, in pixels
   ;  pack:  For testing different image packing algorithms in the subpanels
   ;  rate:  Time difference between subpanels
   ;  hourly:  Make files every hour, rather than every minute.  'rate' will convert to minutes.
   ;  jailbars:  Correct for rare 'jailbars' failure, with dark vertical streaks in the images
   ;  outdir, project, naming_convention, version:  Output filename controls
   ;Example:
   ;  cpi_imagedump, file_search('*.roi'), numcolumns=4, xpanelsize=1200, project='IMPACTS', naming='GHRC'

   IF n_elements(jailbars) eq 0 THEN jailbars = 0  ;Make correction for vertical dead areas
   IF n_elements(res) eq 0 THEN res = 2.3  ;For reference bar
   IF n_elements(rate) eq 0 THEN rate = 5  ;Seconds for new panel.  Minutes if hourly option set.
   IF n_elements(hourly) eq 0 THEN hourly = 0 ;Make hourly images rather than each minute
   IF n_elements(numcolumns) eq 0 THEN numcolumns = 4
   IF n_elements(xpanelsize) eq 0 THEN xpanelsize = 1200
   IF n_elements(ypanelsize) eq 0 THEN ypanelsize = 1000
   IF n_elements(project) eq 0 THEN project = 'project'
   IF n_elements(pack) eq 0 THEN pack = 1
   IF n_elements(outdir) eq 0 THEN outdir=''
   IF n_elements(naming_convention) eq 0 THEN naming_convention='standard'
   IF n_elements(version) eq 0 THEN version='v01'  ;GHRC default

   ;Figure out the size of panels and overall image
   numpanels = 60/rate
   numrows = numpanels/numcolumns

   pad = 25  ;White space between panels
   headerpad = ypanelsize*numrows*0.1 ;100
   panelbackground = 150  ;Background color
   imwidth = xpanelsize*numcolumns + (numcolumns+1)*pad
   imheight = ypanelsize*numrows + (numrows)*pad + headerpad

   ;Make a millimeter scale
   scw = 1000./res +1
   sch = scw/20
   scale = bytarr(scw, sch) + 255
   scale[*,sch/2-2:sch/2+2] = 0    ;Main bar
   scale[0:2,*] = 0                ;Left tick
   scale[-3:-1,*] = 0              ;Right tick
   scale[indgen(10)*scw/10,sch/2-sch/4:sch/2+sch/4] = 0  ;Minor ticks

   loadct, 0
   set_plot, 'z'
   device, /close
   device, set_resolution = [imwidth, imheight]

   ifile = 0L
   openr, lun, fn[ifile], /get_lun

   ;Read file header
   fileheader = {version:0U, year:0U, month:0U, framewidth:0U, frameheight:0U, info:bytarr(70)}
   readu, lun, fileheader

   ;Define file components
   blocktype = 0U

   imageblock = {blksize:0UL, version:0U, numrois:0U, tot:0UL,  $
      day:0B, hour:0B, minute:0B, second:0B, msecond:0U,  $
      type:0U, startx:0U, starty:0U, endx:0U, endy:0U, bgrate:0U, $
      bgpdsthresh:0U, nframes:0UL, ithresh:0B, roierr:0B, roiminsize:0U, $
      roiaspect:0.0, roifill:0.0, roifcount:0UL, imgmean:0B, bkgmean:0B, $
      spare:0U, roixpad:0U, roiypad:0U, strobecount:0UL, framessaved:0UL, $
      imgminval:0B, imgmaxval:0B, nroisaved:0UL, checksum:0U, pdshead:uintarr(3), $
      time:0UL, unknown:uintarr(8)}

   house = {blksize:0UL, version:0U, info:bytarr(98)}

   house2 = {blksize:0UL, version:0U, info:bytarr(172)}

   roiblock = {blksize:0UL, version:0U, startx:0U, starty:0U,  $
      endx:0U, endy:0U, pixbytes:0, flags:0U, length:0.0, $
      startlen:0UL, endlen:0UL, width:0.0, startwidth:0UL, $
      endwidth:0UL, roidepth:0U, area:0.0, perimeter:0.0}

   ;Read file
   ;n = 20000
   ;focus = fltarr(n)
   ;focus2 = fltarr(n)
   lastpanelind = -999
   lastimagetime = '-999'
   IF pack eq 1 THEN BEGIN
      xx = indgen(xpanelsize)
      yy = intarr(xpanelsize)
      yy[0:60] = 40   ;Reserve this place for the second indicators
      yyinit = yy
   ENDIF

   nparticles = 0L
   nwritten = 0L ;Number of particles written, to assess packing efficiency
   finished = 0
   WHILE finished eq 0 DO BEGIN
      readu, lun, blocktype
      CASE blocktype OF
         ;Image block
         'A3D5'XU:  BEGIN
            readu, lun, imageblock
            ;print,'image block'
         END

         ;Housekeeping
         'A1D7'XU: BEGIN
            readu, lun, house
            ;print,'house'
         END

         ;Housekeeping 2
         'A1D9'XU: BEGIN
            readu, lun, house2
            ;print, 'house2'
         END

         ;ROI Image
         'B2E6'XU: BEGIN
            nparticles++
            done = 1
            readu, lun, roiblock
            totx = roiblock.endx - roiblock.startx + 1
            toty = roiblock.endy - roiblock.starty + 1
            roi = bytarr(totx, toty)
            ;Make sure file big enough for roi to exist, else just point to eof
            fs = fstat(lun)
            IF (fs.size - fs.cur_ptr) ge n_elements(roi) THEN readu, lun, roi ELSE point_lun, lun, fs.size
            IF jailbars THEN BEGIN
               ;Make corrections for an error that occurred in IMPACTS, void stripes in data
               roi2 = roi > shift(roi,1) > shift(roi,-1)  ;Move neigbors into void
               w = where(roi ne 0)
               roi2[w] = roi[w]        ;Replace original
               roi2 = median(roi2, 5)  ;Smooth
               roi2[w] = roi[w]        ;Replace original again
               roi = roi2
            ENDIF
            focus2 = max(sobel(roi))   ;Thresh ~200 seems to work well
            ;print,imageblock.day, imageblock.hour, imageblock.minute, imageblock.second, imageblock.msecond

            ;Figure out which image and panel this image belongs to
            IF hourly eq 0 THEN imagetime = string(fileheader.year, fileheader.month, imageblock.day, '_', $
                        imageblock.hour, imageblock.minute, 0, form='(i04,i02,i02,a1,i02,i02,i02)')
            IF hourly eq 1 THEN imagetime = string(fileheader.year, fileheader.month, imageblock.day, '_', $
                        imageblock.hour, 0, 0, form='(i04,i02,i02,a1,i02,i02,i02)')

            IF (imagetime ne lastimagetime) THEN BEGIN
               ;Write current image and start a new one
               IF lastimagetime ne '-999' THEN BEGIN  ;Ignore if very first image
                  pngfile = lastimagetime+'_CPI.png'
                  IF naming_convention eq 'GHRC' THEN BEGIN
                     v = strsplit(lastimagetime,'_', /extract)
                     timedate = v[0]+'-'+v[1]  ;GHRC need dash instead of underscore
                     pngfile = project+'_CPI-P3_'+timedate+'_images_'+version+'.png'
                  ENDIF

                  tv, bytarr(imwidth, imheight)+255 ;White background
                  ;Write image header
                  print, 'Writing '+pngfile

                  timestr = strmid(lastimagetime,0,4)+'/'+strmid(lastimagetime,4,2)+'/'+strmid(lastimagetime,6,2)+' '+strmid(lastimagetime,9,2)+':'+strmid(lastimagetime,11,2)+':'+strmid(lastimagetime,13,2)
                  cgtext, 2*pad, imheight-0.3*headerpad, 'Date/time: ' + timestr, /device, color=0, /font, tt_font='helvetica', charsize=headerpad/70
                  cgtext, 2*pad, imheight-0.5*headerpad, 'Project: '+project+'  Probe: CPI' + '   Resolution: '+ string(res, format='(g0.2)') + ' microns', /device, color=0, /font, tt_font='helvetica', charsize=headerpad/70
                  IF hourly eq 0 THEN cgtext, 2*pad, imheight-0.7*headerpad, 'This image represents one minute of flight time, one panel every '+strtrim(string(rate),2)+' seconds.', /device, color=0, /font, tt_font='helvetica', charsize=headerpad/70
                  IF hourly eq 1 THEN cgtext, 2*pad, imheight-0.7*headerpad, 'This image represents one hour of flight time, one panel every '+strtrim(string(rate),2)+' minutes.', /device, color=0, /font, tt_font='helvetica', charsize=headerpad/70
                  cgtext, 2*pad, imheight-0.9*headerpad, 'Many more images are not shown.  Contact PI or see raw data for complete imagery.', /device, color=0, /font, tt_font='helvetica', charsize=headerpad/70

                  ;Write scale
                  tv, scale, imwidth-scw-2*pad, imheight-sch-2*pad, /device
                  cgtext, imwidth-scw/2-2*pad, imheight-sch-4*pad, '1 mm', /device, color=0, /font, tt_font='helvetica', charsize=headerpad/100, align=0.5

                  ;Write panels
                  FOR icolumn = 0, numcolumns-1 DO BEGIN
                     FOR irow = 0, numrows-1 DO BEGIN
                        ipanel = icolumn + (irow*numcolumns)
                        ;Reverse panel to make origin at top-left corner
                        tv, reverse(panel[ipanel,*,*],3), icolumn*(xpanelsize+pad)+pad, imheight-headerpad-ypanelsize-irow*(ypanelsize+pad)
                        cgtext, icolumn*(xpanelsize+pad)+pad+10, imheight-headerpad-irow*(ypanelsize+pad)-35, string(rate*ipanel, format='(i0)'), /device, color=255, /font, tt_font='helvetica', charsize=headerpad/100
                     ENDFOR
                  ENDFOR

                  ;Save image
                  write_png, outdir+pngfile, tvrd()
               ENDIF

               ;Reset z-buffer image
               device, /close
               device, set_resolution = [imwidth, imheight]

               ;Reset panels
               lastimagetime = imagetime
               lastpanelind = -999
               panel = bytarr(numpanels, xpanelsize, ypanelsize) + panelbackground
            ENDIF

            IF hourly eq 0 THEN panelind = fix(imageblock.second/rate)
            IF hourly eq 1 THEN panelind = fix(imageblock.minute/rate)
            IF panelind ne lastpanelind THEN BEGIN
               ;Reset positions describing last image position
               xpos = 0
               ypos = 0
               lastpanelind = panelind
               IF pack eq 1 THEN yy = yyinit
            ENDIF

            ;Write image to current panel
            ;     See https://en.wikipedia.org/wiki/Strip_packing_problem  online variant
            IF pack eq 0 THEN BEGIN
               ;Overwrite every image in the corner
               xmin = xpos
               xmax = xpos+totx-1
               ymin = ypos
               ymax = ypos+toty-1
               IF (xmax lt xpanelsize) and (ymax lt ypanelsize) and (focus2 gt 150) THEN panel[panelind, xpos:xpos+totx-1, ypos:ypos+toty-1] = roi
            ENDIF

            IF pack eq 1 THEN BEGIN
               ;Homebrew method, keep track of y-height and find best location.
               ;  Does not shift particles to the left over open gaps, tends to make 'towers'
               s = sort(yy)  ;Start searching at minimum y-height
               j = 0
               gotplacement = 0
               REPEAT BEGIN
                  ;Find position where roi fits inside the panel, and yy (y-height) does not increase further right which would intercept roi
                  IF (xx[s[j]]+totx lt xpanelsize) && (yy[s[j]]+toty lt ypanelsize) && (max(yy[s[j]:s[j]+totx]) le yy[s[j]]) THEN BEGIN
                     ix = xx[s[j]]   ;Save locations
                     iy = yy[s[j]]
                     gotplacement = 1
                  ENDIF ELSE j++
               ENDREP UNTIL (gotplacement eq 1) or (j eq xpanelsize)   ;Stop when searched all y-heights
               IF (gotplacement eq 1) and (focus2 gt 150) THEN BEGIN
                  panel[panelind, ix:ix+totx-1, iy:iy+toty-1] = roi
                  yy[ix:ix+totx-1] = iy+toty-1   ;Update y-height over region of this roi placement
                  nwritten++
               ENDIF
            ENDIF

            IF pack eq 2 THEN BEGIN
            ENDIF

         END
         ELSE: stop,'Unknown block type'; finfo.badcount = finfo.badcount + 1
      ENDCASE

      IF eof(lun) THEN BEGIN
         ifile++
         IF ifile lt n_elements(fn) THEN BEGIN
            close, lun
            openr, lun, fn[ifile]
            readu, lun, fileheader
         ENDIF ELSE finished = 1
      ENDIF

   ENDWHILE
   close, lun
   IF !version.os_family eq 'Windows' THEN set_plot,'win' ELSE set_plot,'x'
   print, 'Num Particles: ',nparticles,'   Num Written:', nwritten

END
