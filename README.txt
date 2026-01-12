■ WELCOME
  This is a very short guide to using rivctl.

  You can scroll through this article with
  [↑↓] keys. To exit hit [Enter] or [Esc].

■ RETRIEVING PAGES
  When rivctl captures a debug packet it creates
  a new "page" and appends it to the database
  A single page captures all registers value,
  program counter value and a small chunk
  of data memory.

  You can move between pages using [←→] keys.
  If you wish to see only the latest package hit
  a [L] key. Also you can navigate to specific
  page by pressing [N] key and entering your
  desired page number. All of these actions are
  available through "Page" menu with [P] key.

  The data memory view is fixed and not scroll-
  able, due to rather small packet size. The
  viewport can be only adjusted for new packets.
  Changing the offset sends a special command
  under the hood to the CPU.

■ SENDING COMMANDS
  To aid in debugging the CPU can be controlled 
  via UART commands, sent from the host computer.

  These commands can be triggered via simple
  keystrokes:

  [h]   halt the CPU completely
  [z]   run the CPU at max. speed
  [a]   execute next instruction
  [s]   step through CPU states manually
  [r]   reset the CPU (but not memories)

  Program upload can be found in "File" > "Upload" 
  menu, opened with [F] key, or by hitting [U] key.

  A simple file picker will open. You can enter
  directories by selecting them and hitting 
  [Enter] key, similarly you can go to parent
  directory by selecting "../" entry.

  When you select a file ~ colored white ~, a
  program preview will popup. You can scroll through
  the listing with [↑↓] keys, and switch between 
  dialog buttons with [←→] keys. Hitting "upload"
  will push the program to the packet queue and 
  start sending the instruction stream to the CPU.

■ TOPBAR
  ~ light-blue bar near the top of the screen ~
  Topbar is used for displaying actions relevant
  to current pane. Panes can be switched with
  [Tab] key.

  Apart from that, there is a simple page count
  with current page and a CPU mode display. 

  At the moment there are 2 menus available: 
  "File" and "Page", opened with [F] and [P] keys
  consecutively. For those who do not prefer
  using menus, I've provided a number of hotkeys:

  File actions hotkeys:
  [H]   display this help message
  [S]   save all collected pages as a sqlite3 .db
        file to a specified location
  [U]   display program upload dialog
  [Q]   quit this program.

  Page actions hotkeys:
  [N]   navigate to particular page
  [L]   always display latest page - you can break
        out of this mode by pressing left or right
        arrow key or by jumping to a specific page

■ TASKBAR
  ~ black bar near the bottom of the screen ~
  Taskbar consists of two parts. A small list of
  most debug actions will always be displayed in
  the left part of the bar.

  On the right side, an UART status is shown. 
  Upon receiving data from the port a green indi-
  cator will flash briefly. Similarly yellow indi-
  cator flashes on command transmission. The text
  next to the indicators is a shorten device name.

  
      Thank you for using rivctl!
        Szymon Miekina, Nov 2025
