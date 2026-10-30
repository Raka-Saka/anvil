# Chrono OS v4 - Improved Roadmap
## Lessons Applied, Walls Avoided

**Created:** January 2, 2026
**Goal:** Reach a functional, usable OS - not just a tech demo

---

## Why Previous Versions Hit Walls

### Wall 1: Source Code Loss
- **Cause:** Ephemeral session storage, no regular commits
- **Solution:** Commit after EVERY milestone, push immediately

### Wall 2: xHCI After ExitBootServices
- **Cause:** Controller reset kills SuperSpeed link
- **Solution:**
  - Phase 1: UEFI-mode USB logging only (before ExitBootServices)
  - Phase 2: Preserve UEFI state in kernel mode
  - Fallback: AHCI logging if USB fails

### Wall 3: Overambitious Scope
- **Cause:** Trying to build everything at once
- **Solution:** Each milestone = demonstrable progress, usable state

### Wall 4: No Persistence Early
- **Cause:** TSS designed but SSD writes delayed
- **Solution:** Simple sector read/write FIRST, fancy TSS later

### Wall 5: No Input After ExitBootServices
- **Cause:** PS/2 keyboard driver came late
- **Solution:** Keyboard in M2, not M5

---

## Critical Success Criteria

**"Functional OS" means:**
1. Boots reliably from USB on Aorus X3
2. Displays text on screen (readable at 3200x1800)
3. Accepts keyboard input
4. Can read/write to SSD
5. Persists data across reboots
6. Has interactive shell with useful commands

**Everything else is enhancement.**

---

## Phase 0: Foundation (M1-M2) - "Can I See and Type?"

### M1: Boot + Display ✓ COMPLETE
**Goal:** Boot, show text, prove we're alive
**Verified:** January 2, 2026 on Aorus X3

**Deliverables:**
- [x] UEFI entry with gnu-efi
- [x] GOP framebuffer (3200x1800)
- [x] Bitmap font (8x16, scaled 2x for HiDPI)
- [x] Serial output (COM1 @ 115200) for debugging
- [x] Basic string/memory utilities
- [x] USB file logging (BOOTLOG.TXT)
- [x] MinGW-compatible build system

**Hardware Verified (from BOOTLOG_001):**
```
Framebuffer: 0xD0000000
Resolution: 3200x1800
Pitch: 12800 bytes
VRAM: 23,040,000 bytes (~22 MB)
```

**Success Test:** ALL PASSED
- USB boots on Aorus X3 ✓
- Text visible on screen ✓
- Log file written to USB ✓
- Keyboard input detected ✓

**Commit:** `M1: Boot + Framebuffer complete`

### M2: Input + Hardware Survey ✓ COMPLETE
**Goal:** Accept keyboard input while in UEFI mode
**Verified:** January 2, 2026 on Aorus X3

**Deliverables:**
- [x] UEFI keyboard input (before ExitBootServices)
- [x] Simple command prompt loop
- [x] Parse basic commands (help, info, clear, halt, reboot)
- [x] Display hardware info (PCI scan, memory map)
- [x] Timestamped log files (BOOTLOG_YYYYMMDD_HHMMSS.TXT)

**Commands Implemented:**
- `help` - Show available commands
- `info` - UEFI firmware info
- `pci` - Scan PCI bus
- `mem` - Show memory map
- `clear` - Clear screen
- `reboot` - Cold reboot
- `halt` - Save log and halt

**Success Test:** ALL PASSED
- Type commands, see responses ✓
- `pci` shows devices ✓
- `halt` saves log file ✓

**Commit:** `M2: UEFI Input + Hardware Survey complete`

---

## Phase 1: Storage (M3-M4) - "Can I Save Things?"

### M3: AHCI Storage ✓ COMPLETE
**Goal:** Read and write SSD sectors
**Verified:** January 2, 2026 on Aorus X3

**Deliverables:**
- [x] AHCI controller detection (hardcoded ABAR fallback for Aorus X3)
- [x] Port initialization with command list, FIS, command table
- [x] IDENTIFY DEVICE (with correct W-bit!)
- [x] READ DMA EXT
- [x] WRITE DMA EXT (with cache flush!)

**Hardware Verified:**
```
AHCI Version: 0x00010300 (AHCI 1.3)
CAP: 0xC330FF45
PI: 0x00000003 (Ports 0 and 1)
Port 0: SATA device identified
Port 1: SATA device identified
```

**Success Test:** ALL PASSED
- `disk` shows both drives ✓
- `read 0` shows sector data ✓
- Sector read/write working ✓

**Commit:** `M3 VERIFIED: AHCI Storage Driver on Aorus X3`

### M4: Simple Persistence ✓ COMPLETE
**Goal:** Save and load data across reboots
**Verified:** January 2, 2026 on Aorus X3

**Deliverables:**
- [x] KVStore at LBA 0x100000 (safe area on SSD)
- [x] Simple key-value store (8 sectors = 4KB)
- [x] `save <key> <value>` command
- [x] `load <key>` command
- [x] Boot counter that increments each boot
- [x] Automatic sync before halt/reboot

**Success Test:** ALL PASSED
- `save greeting Hello` ✓
- Reboot ✓
- `load greeting` shows "Hello" ✓
- Boot counter increments correctly ✓

**Commit:** `M4 VERIFIED: Simple Persistence on Aorus X3`

---

## Phase 2: Kernel Mode (M5-M6) - "Can I Run Standalone?"

### M5: ExitBootServices Transition ✓ COMPLETE
**Goal:** Leave UEFI, run on bare metal
**Verified:** January 3, 2026 on Aorus X3

**Deliverables:**
- [x] Save all hardware addresses before exit
- [x] Get and save memory map
- [x] ExitBootServices call
- [x] GDT setup (64-bit long mode with TSS)
- [x] Polling-mode PS/2 keyboard driver
- [x] AHCI-based kernel logging to SSD
- [x] `klog` command to read kernel log
- [x] `saveklog` command to export to USB

**Success Test:** ALL PASSED
- Transition to kernel mode without crash ✓
- Keyboard input works (polling) ✓
- Kernel log persists to SSD ✓
- Log exportable to USB for offline debugging ✓

**Commit:** `M5 VERIFIED: ExitBootServices + Kernel Mode on Aorus X3`

### M6: Interrupts (IDT/PIC/PIT) ✓ COMPLETE
**Goal:** Enable hardware interrupts for timer and keyboard
**Verified:** January 3, 2026 on Aorus X3

**Deliverables:**
- [x] IDT setup (256 entries)
- [x] PIC remapping (IRQ 0-15 to INT 32-47)
- [x] PIT timer at 100 Hz
- [x] Timer interrupt handler (IRQ0)
- [x] Keyboard interrupt handler (IRQ1)
- [x] Clear debug registers before STI
- [x] Naked function ISR handlers

**Hardware Verified:**
```
[KERNEL] Enabling interrupts (STI)...
[KERNEL] Interrupts ENABLED!
[KERNEL] Timer ticks after delay: 199
Timer ticks: 3432 (~34 seconds)
```

**Success Test:** ALL PASSED
- Timer interrupt firing at 100 Hz ✓
- Keyboard interrupt capturing input ✓
- No exceptions after STI ✓
- `ticks` command shows timer count ✓

**Commit:** `M6 VERIFIED: Interrupts Working on Aorus X3`

---

## Phase 3: TSS Foundation (M7-M8) - "Time Becomes Real"

### M7: Content-Addressed Storage ✓ COMPLETE
**Goal:** Store data by hash
**Verified:** January 3, 2026 on Aorus X3

**Deliverables:**
- [x] SHA-256 implementation
- [x] Block allocation bitmap
- [x] Content-addressed block storage
- [x] Deduplication (same content = same block)
- [x] `store <data>` returns hash
- [x] `retrieve N` returns data by index

**Success Test:** ALL PASSED
- Store "hello world" twice, uses same block ✓
- Retrieve by index works ✓
- caslist shows entries with ref counts ✓
- casstats shows deduplication stats ✓

**Commit:** `M7 VERIFIED: Content-Addressed Storage on Aorus X3`

### M8: Moments ✓ COMPLETE
**Goal:** Create and navigate snapshots
**Verified:** January 3, 2026 on Aorus X3

**Deliverables:**
- [x] Moment structure (id, timestamp, parent, content hash)
- [x] `moment create <tag>` - create snapshot
- [x] `moment list` - show all moments
- [x] `moment show <id>` - display moment details
- [x] `moment goto <id>` - time travel!
- [x] Session logging (auto-capture console output)

**Success Test:** ALL PASSED
- Created multiple moments with tags ✓
- List shows moments with timestamps ✓
- `goto` shows historical session ✓
- Moments persist across reboots ✓

**Commit:** `M8 VERIFIED: Moments - Time Travel Works!`

---

## Phase 4: Usability (M9-M10) - "Daily Driver Foundation"

### M9: File Operations ✓ COMPLETE
**Goal:** Work with files, not just raw data
**Verified:** January 3, 2026 on Aorus X3

**Deliverables:**
- [x] Tree structure (directories)
- [x] `ls` - list directory contents
- [x] `cat <file>` - display file
- [x] `write <file> <content>` - create/update file
- [x] `mkdir <dir>` - create directory
- [x] Every write creates a moment (versioning)
- [x] `cd <path>` - change directory
- [x] `pwd` - print working directory
- [x] `rm <name>` - remove file/directory
- [x] `fsstat` - show filesystem statistics

**Implementation Details:**
- Storage at LBA 0x100400 (32 sectors = 16KB for index)
- Max 256 nodes (files + directories)
- File content stored in CAS (deduplication)
- Automatic moment creation on file writes

**Success Test:**
- Create files and directories
- `ls` shows them
- `cat` displays file content
- Data persists across reboot
- Modify file, both versions accessible via moments

**Commit:** `M9: File Operations complete`

### M10: USB Logging - SKIPPED
**Goal:** Log to USB drive for external backup

**Status:** Skipped - existing logging is sufficient
- BOOTLOG_*.TXT files already written to USB on boot
- `saveklog` exports kernel log to USB
- AHCI logging to SSD works reliably

**May revisit later if needed.**

---

## Phase 5: Polish (M11-M12) - "Ready for Daily Use"

### M11: Shell Improvements ✓ COMPLETE
**Goal:** Comfortable interactive experience
**Verified:** January 3, 2026 on Aorus X3

**Deliverables:**
- [x] Command history (up/down arrows)
- [x] Tab completion for files/directories
- [x] `diff <moment1> <moment2>` - compare moments
- [x] `search <term>` - find in moments
- [x] `help <command>` - detailed help per command

**Implementation Details:**
- History: Circular buffer of 16 commands, up/down arrow navigation
- Tab completion: Matches file/directory names in current directory
- diff: Shows size comparison, first difference with context
- search: Case-sensitive search across all moment session logs
- help: Detailed usage for moment, diff, search, ls, cd, write, store, kernel, save/load, fsck

**Commit:** `M11: Shell Improvements complete`

### M12: Reliability ✓ COMPLETE
**Goal:** Handle errors gracefully
**Verified:** January 3, 2026

**Deliverables:**
- [x] Disk error recovery (AHCI retry logic with port reset)
- [x] Backup superblocks for all storage systems
  - KVStore: LBA 0x100008 (backup copy)
  - CAS: LBA 0x100A10 (superblock), 0x100A18 (index)
  - Moments: LBA 0x100320
  - FS: LBA 0x100440
- [x] `fsck` command for storage integrity checking
  - Verifies CAS: magic, bitmap vs index consistency
  - Verifies FS: node count, parent references
  - Auto-corrects minor inconsistencies
- [x] Clean shutdown with full data flush
  - Syncs CAS and KVStore on halt/reboot
  - Shows "Clean Shutdown (M12)" banner

**Commit:** `M12: Reliability complete - v4.0 Release!`

---

## Development Workflow

### Every Session:
1. Pull latest: `git pull`
2. Make changes
3. Test on real hardware via USB
4. Document in ENGINEERING_LOG_V4.md
5. Commit with descriptive message
6. Push: `git push`

### USB Transfer Workflow:
```
Desktop (F:\chronos\)  -->  USB Key  -->  Aorus X3 Laptop
     |                        |                |
  Build here           Transfer .img      Boot from USB
  Edit code            Copy logs back     Test on hardware
```

### After Each Milestone:
```bash
git add -A
git commit -m "M<N>: <Milestone Name> complete"
git push
```

---

## Risk Mitigation

### If xHCI fails completely:
- Use AHCI logging only
- Skip M10, proceed to M11
- USB not required for functional OS

### If ExitBootServices causes issues:
- Stay in UEFI mode longer
- Implement more features before transition
- Fallback: UEFI-only mode is still useful

### If font is unreadable:
- 3x scaling for 3200x1800 (already planned)
- Fallback to 2x if 3x too large

### If SSD write fails:
- Double-check W-bit (AHCI_CMD_WRITE = bit 6)
- Verify cache flush (wbinvd)
- Test with read-after-write verification

---

## Success Metrics

| Milestone | Key Metric | Status |
|-----------|------------|--------|
| M1 | Text visible on Aorus X3 screen | ✓ DONE |
| M2 | Can type and see response | ✓ DONE |
| M3 | `disk` shows both drives | ✓ DONE |
| M4 | Data persists across reboot | ✓ DONE |
| M5 | Kernel runs, keyboard works | ✓ DONE |
| M6 | Timer ticks, interrupts work | ✓ DONE |
| M7 | Deduplication verified | ✓ DONE |
| M8 | Time travel works | ✓ DONE |
| M9 | Files and directories work | ✓ DONE |
| M10 | USB log saved (optional) | SKIPPED |
| M11 | History and completion work | ✓ DONE |
| M12 | No data loss under stress | ✓ DONE |

---

---

## Phase 6: True OS Foundation (M14) - "Memory Management"

### M14: Memory Management Foundation ✓ COMPLETE
**Goal:** Transform from UEFI application into true OS with proper memory management
**Verified:** January 3, 2026 on Aorus X3

**Deliverables:**
- [x] Physical Memory Manager (PMM)
  - Bitmap allocator (1 bit per 4KB page)
  - Captures UEFI memory map before ExitBootServices
  - `pmm_alloc_page()` / `pmm_free_page()` functions
  - Reserves first 3MB for kernel
- [x] Virtual Memory Manager (VMM)
  - x86-64 4-level paging (PML4 → PDPT → PD → PT)
  - Identity maps first 4GB using 2MB huge pages
  - Replaces UEFI's page tables with our own
  - Page fault handler (INT 14) with CR2 diagnostics
- [x] Kernel Heap Allocator
  - Free-list allocator with block coalescing
  - `kmalloc()` / `kfree()` / `kzalloc()` functions
  - 1MB initial heap from PMM
  - Magic values for corruption detection

**New Kernel Shell Commands:**
| Command | Description |
|---------|-------------|
| `pmm` | Show physical memory stats (total/free/used pages) |
| `vmm` | Show virtual memory stats (CR3, page tables) |
| `heap` | Show heap stats with integrity check |
| `alloc` | Test kmalloc(1024)/kfree cycle |

**Kernel Mode Initialization (updated):**
1. [2/6] Captures UEFI memory map for PMM
2. [5/6] Calls ExitBootServices
3. [6/6] Initializes CPU (GDT, IDT, PIC, PIT)
4. Initializes PMM with captured memory map
5. Initializes VMM (switches to our page tables)
6. Initializes Heap (1MB from PMM)

**Files Created:**
- `include/pmm.h` - PMM interface
- `include/vmm.h` - VMM interface
- `include/heap.h` - Heap interface
- `src/lib/pmm.c` - Bitmap page allocator
- `src/lib/vmm.c` - 4-level paging
- `src/lib/heap.c` - Free-list allocator

**Files Modified:**
- `src/lib/shell.c` - PMM capture, VMM/heap init
- `src/lib/cpu.c` - Page fault handler, memory commands
- `Makefile.mingw` - Added new sources

**Hardware Verified (KERNELLOG_010_M14):**
```
PMM:
  Total pages: 3,977,022 (~15.2 GB)
  Free pages:  3,976,097
  Used pages:  925

VMM:
  CR3 (PML4): 0x00000000B92CE000
  Page tables: 6
  Identity mapped: 0-4GB

Heap:
  Total: 1024 KB
  Free:  1024 KB
  Integrity: OK
```

**Success Test:** ALL PASSED
- `pmm` shows ~15GB RAM detected ✓
- `vmm` shows our CR3 value ✓
- `heap` shows 1MB heap with OK integrity ✓
- No crashes on kernel transition ✓

**Commit:** `M14 VERIFIED: Memory Management on Aorus X3`

---

## Phase 7: Chrono-Native Timeline System (M15) - "Timelines Replace Processes"

### M15: Timeline Infrastructure ✓ COMPLETE
**Goal:** Implement the foundational Chrono-native timeline system
**Verified:** January 3, 2026 on Aorus X3

**Design Philosophy:**
Instead of traditional Unix processes, Chrono OS uses **Timelines** as the primary execution abstraction:
- **Timeline**: An evolving sequence of Moments with full history
- **Moment**: Immutable snapshot (memory tree hash + CPU registers + timestamp)
- **Memory Tree**: Page tables stored in CAS with structural sharing (like Git)
- **Time Travel**: Navigate to any previous moment in a timeline
- **Branching**: O(1) fork by sharing parent's moments

**Deliverables:**
- [x] Timeline structure (id, name, state, head moment, parent)
- [x] Moment structure (id, hash, parent, memory root, registers, timestamp, tag)
- [x] Memory tree structures mirroring x86-64 page tables
- [x] `timeline_init()` - creates root timeline with genesis moment
- [x] `timeline_branch(name)` - O(1) branching via shared moments
- [x] `chrono_moment_create(tag, flags)` - capture current state
- [x] `moment_travel_to(moment)` - time travel to previous moment
- [x] Integration with kernel heap (`kmalloc`/`kfree`)

**Kernel Shell Commands:**
| Command | Description |
|---------|-------------|
| `timeline`, `tl` | List all timelines |
| `moments`, `ml` | List moments in current timeline |
| `checkpoint [tag]` | Create a moment snapshot |
| `branch <name>` | Create new timeline branch |
| `travel <id>` | Time travel to moment by ID |

**Files Created:**
- `include/timeline.h` - Timeline and Moment structures
- `include/memtree.h` - Memory tree node structures
- `src/lib/timeline.c` - Timeline/moment management
- `src/lib/memtree.c` - Memory tree operations

**Files Modified:**
- `src/lib/shell.c` - Added timeline_init() call in kernel mode
- `src/lib/cpu.c` - Added timeline commands to kernel shell
- `Makefile.mingw` - Added new sources

**Hardware Verified (KERNELLOG_011_TIMELINE):**
```
[KERNEL] kernel_shell_run starting
  Kernel Shell Ready
  Commands: help, ticks, flush, halt, reboot
  Timeline: timeline, moments, checkpoint, branch, travel

[CMD] checkpoint test
  Created checkpoint 'test'
```

**Success Test:** ALL PASSED
- `timeline` shows root timeline ✓
- `moments` shows genesis moment ✓
- `checkpoint test` creates new moment ✓
- Commands recognized in kernel shell ✓

**Commit:** `M15 VERIFIED: Chrono-Native Timeline System on Aorus X3`

---

## Phase 8: Process Foundation (M16-M17) - "Multiple Execution Contexts"

### M16: Task Structure + Kernel Threads ✓ COMPLETE
**Goal:** Define process abstraction, create multiple kernel tasks
**Verified:** January 3, 2026 on Aorus X3

**Dependencies:** M14 (PMM/VMM/Heap for allocating task structures and stacks)

**Deliverables:**
- [x] `task_struct` definition:
  - `pid` - unique process ID
  - `state` - RUNNING, READY, BLOCKED, ZOMBIE
  - `registers` - saved CPU state (RAX-R15, RIP, RSP, RFLAGS, CR3)
  - `kernel_stack` - 16KB per task
  - `page_tables` - PML4 pointer (for future per-process spaces)
  - `name` - task name for debugging
  - `next`/`prev` - task list pointers
- [x] Task list management:
  - `task_create(name, entry_point)` - allocate and initialize task
  - `task_destroy(pid)` - clean up task resources
  - `task_get_current()` - return current running task
  - `task_get_by_pid(pid)` - find task by PID
- [x] Initial tasks:
  - Task 0: Idle task (runs HLT in loop when nothing else)
  - Task 1: Shell task (current shell becomes a task)
- [x] Shell command: `ps` - list all tasks with PID, state, name

**Hardware Verified (KERNELLOG_012_M16_TASKS):**
```
  Task List:
  ----------
  PID  STATE    NAME
  ---  -------  ----------------
    0  READY    idle
    1  RUNNING  shell *

  Total: 2 tasks (* = current)
```

**Success Test:** ALL PASSED
- `ps` shows idle task (PID 0) and shell task (PID 1) ✓
- Both tasks exist in task list ✓
- Current task pointer is valid (shell marked with *) ✓

**Files Created:**
- `include/task.h` - task structures and API
- `src/lib/task.c` - task management

**Files Modified:**
- `src/lib/cpu.c` - integrate task system, add `ps` command

**Commit:** `M16 VERIFIED: Task Structure on Aorus X3`

---

### M17: Context Switching ✓ COMPLETE
**Goal:** Switch execution between kernel tasks
**Verified:** January 6, 2026 on Aorus X3

**Dependencies:** M16 (task structures must exist)

**Deliverables:**
- [x] Register save/restore:
  - Pure assembly `context_switch()` in `src/lib/switch.S`
  - Saves/restores callee-saved registers: RBX, RBP, R12-R15
  - **Critical:** Uses Microsoft x64 ABI (RCX, RDX), not System V (RDI, RSI)
- [x] Stack switching:
  - Each task has 16KB kernel stack
  - TSS.RSP0 updated via `tss_set_rsp0()` on task switch
  - `task_setup_stack()` prepares initial stack for new tasks
- [x] Cooperative switching:
  - `yield()` - voluntarily give up CPU to next ready task
  - `switch_to(next_task)` - low-level context switch
  - `schedule()` - round-robin task selection
- [x] Task state transitions:
  - READY → RUNNING (when scheduled)
  - RUNNING → READY (when yielding)
  - RUNNING → BLOCKED (when waiting)
  - BLOCKED → READY (when woken)
- [x] Shell commands: `spawn`, `yield`
- [x] Task entry trampoline for new task startup
- [x] Idle task yields after interrupt wake (enables round-robin)

**Critical Bug Fixed (2 days debugging):**
Assembly used System V ABI (RDI/RSI) but UEFI/MinGW uses Microsoft x64 ABI (RCX/RDX).

**Hardware Verified (KERNELLOG_20260106_063736.TXT):**
```
[CMD] spawn
  Created task 'test' (PID 2)
[CMD] yield
  Yielding CPU...
  Returned from yield
```

**Success Test:** ALL PASSED
- `spawn` creates test task ✓
- `yield` switches between tasks ✓
- Shell prompt returns after yield ✓

**Files Created:**
- `src/lib/switch.S` - Pure assembly context_switch (MS x64 ABI)

**Files Modified:**
- `include/task.h` - context switch declarations
- `src/lib/task.c` - switch_to, yield, schedule, task_setup_stack
- `src/lib/cpu.c` - spawn/yield commands, test_task_entry
- `Makefile.mingw` - assembly compilation rules

**Commit:** `M17 VERIFIED: Context Switching Works on Aorus X3`

---

## Phase 9: Preemptive Multitasking (M18) - "Time Slicing"

### M18: Scheduler + Preemption ✓ VERIFIED
**Goal:** Automatic task switching driven by timer interrupt
**Verified:** January 6, 2026 on Aorus X3

**Dependencies:** M17 (context switching must work), M6 (timer interrupt)

**Deliverables:**
- [x] Scheduler:
  - `schedule()` - round-robin task selection
  - Task list iteration for ready queue
  - Time slice tracking (`g_slice_ticks`)
- [x] Preemption (voluntary kernel preemption):
  - Timer sets `g_need_resched` when slice expires (10 ticks = 100ms)
  - `check_resched()` at yield points triggers switch
  - Safer than interrupt-context switching for kernel code
- [x] Synchronization primitives:
  - `preempt_disable()` / `preempt_enable()` - preemption control
  - `spinlock_acquire()` / `spinlock_release()` - basic locking
- [x] Blocking primitives:
  - `task_sleep(ticks)` - block for N timer ticks
  - `task_wake(task)` - wake blocked task
  - `scheduler_tick()` wakes sleeping tasks
- [x] Yield points:
  - `kbd_getchar_blocking()` calls `check_resched()` after `hlt`

**Implementation Notes:**
- Voluntary kernel preemption (flag + yield point) vs interrupt-context
- `reset_slice()` in `switch_to()` gives new task full slice
- Task output may interleave with shell (no terminal mux)

**Success Test:** ALL PASSED
- [x] Test task via `spawn` prints count 0-4, exits to ZOMBIE
- [x] Preemption at yield points works
- [x] 100ms time slices verified
- [x] No deadlocks or crashes

**Files Modified:**
- `src/lib/task.c` - scheduler_tick, check_resched, reset_slice
- `src/lib/cpu.c` - check_resched() in kbd_getchar_blocking
- `include/task.h` - M18 declarations

**Commit:** `M18 VERIFIED: Preemptive Multitasking on Aorus X3`

---

## Phase 10: User Space (M19-M21) - "Ring 3 Execution"

### M19: User Mode Basics ✓ VERIFIED
**Goal:** Run code in ring 3 with separate address space
**Verified:** January 7, 2026 on Aorus X3

**Dependencies:** M18 (scheduler), M14 (VMM for address spaces)

**Deliverables:**
- [x] Per-process address spaces:
  - Each task gets own PML4
  - Kernel mapped in upper half (0xFFFF800000000000+)
  - User space in lower half (0x0000000000000000 - 0x00007FFFFFFFFFFF)
- [x] User mode transition:
  - `iret` to ring 3 with user CS/SS selectors
  - User stack allocation in user address space
  - GDT user segments already exist (verify)
- [x] Return to kernel:
  - Interrupt/exception from user mode
  - TSS.RSP0 provides kernel stack
- [x] Test program:
  - Simple inline user code (not ELF yet)
  - Runs in ring 3, triggers syscall to exit

**Success Test:** ALL PASSED
- [x] Task runs in ring 3 (verified via syscall)
- [x] Page fault handling works (USER bit fix)
- [x] Return to kernel via INT 0x80 works
- [x] User code prints via syscalls

**Files to Create:**
- `include/user.h` - user space definitions
- `src/lib/user.c` - user mode support

**Files to Modify:**
- `src/lib/task.c` - user/kernel task distinction
- `src/lib/vmm.c` - per-process address spaces

---

### M20: System Calls
**Goal:** Safe interface between user programs and kernel

**Dependencies:** M19 (user mode execution)

**Deliverables:**
- [ ] Syscall mechanism:
  - Option A: `SYSCALL/SYSRET` (fast, MSR setup required)
  - Option B: `INT 0x80` (simpler, slower)
  - Choose based on complexity tradeoff
- [ ] Syscall table:
  - Array of function pointers
  - Syscall number in RAX
  - Arguments in RDI, RSI, RDX, R10, R8, R9
  - Return value in RAX
- [ ] Initial syscalls:
  - `sys_exit(code)` - terminate process
  - `sys_write(fd, buf, len)` - write to console (fd=1)
  - `sys_getpid()` - return current PID
  - `sys_yield()` - voluntary reschedule
- [ ] User library stubs:
  - `_exit()`, `write()`, `getpid()`, `yield()`

**Success Test:**
- User program calls `write(1, "Hello", 5)` and text appears
- User program calls `exit(42)` and terminates with code 42
- `getpid()` returns correct PID

**Files to Create:**
- `include/syscall.h` - syscall numbers and declarations
- `src/lib/syscall.c` - syscall dispatcher and implementations

**Files to Modify:**
- `src/lib/cpu.c` - syscall entry point (IDT or MSRs)

---

### M21: ELF Loader
**Goal:** Load and execute ELF64 binaries

**Dependencies:** M20 (syscalls for program to use)

**Deliverables:**
- [ ] ELF64 parser:
  - Validate ELF magic and type (ET_EXEC)
  - Parse program headers (PT_LOAD segments)
  - Find entry point (e_entry)
- [ ] Segment loading:
  - Allocate pages for each PT_LOAD segment
  - Map at correct virtual address (p_vaddr)
  - Copy segment data (p_filesz bytes)
  - Zero remainder (p_memsz - p_filesz for BSS)
  - Set page permissions (read/write/execute)
- [ ] Process setup:
  - Allocate user stack
  - Set up argc/argv on stack (initially empty)
  - Jump to entry point in ring 3
- [ ] Shell command: `exec <filename>` - load and run ELF from filesystem
- [x] Test program:
  - Cross-compile simple C program to ELF64
  - Store in Chrono filesystem
  - Execute via `exec` command

**Success Test:**
- `exec hello` loads and runs hello.elf
- Program prints "Hello from user space!"
- Program exits cleanly

**Files to Create:**
- `include/elf.h` - ELF64 structures
- `src/lib/elf.c` - ELF loader

**Files to Modify:**
- `src/lib/shell.c` - add `exec` command (UEFI shell) or
- `src/lib/cpu.c` - add `exec` command (kernel shell)

---

## Phase 11: IPC & Process Management (M22-M23) - "Process Lifecycle"

### M22: Fork & Wait
**Goal:** Create child processes and wait for them

**Dependencies:** M21 (need processes to fork)

**Deliverables:**
- [ ] `fork()` syscall:
  - Clone current process
  - Copy address space (or COW - copy on write)
  - Child gets PID, parent gets child's PID, child gets 0
- [ ] `wait(status)` / `waitpid(pid, status)` syscalls:
  - Parent blocks until child exits
  - Retrieve exit code
  - Clean up zombie process
- [ ] Process states:
  - ZOMBIE - exited but parent hasn't waited
  - Proper cleanup when parent waits
- [ ] Orphan handling:
  - Reparent to init (PID 1) if parent dies

**Success Test:**
- Parent forks child
- Child runs, exits with code
- Parent waits, gets exit code
- No zombies left behind

**Files to Modify:**
- `src/lib/syscall.c` - add fork, wait, waitpid
- `src/lib/task.c` - process cloning and cleanup

---

### M23: Pipes & Signals
**Goal:** Inter-process communication

**Dependencies:** M22 (need multiple processes)

**Deliverables:**
- [ ] Anonymous pipes:
  - `pipe(fds[2])` syscall - create pipe
  - `read(fd, buf, n)` - read from pipe
  - `write(fd, buf, n)` - write to pipe
  - Blocking when empty/full
  - EOF when write end closed
- [ ] Signals:
  - `kill(pid, sig)` syscall
  - Signal handlers (or default actions)
  - SIGKILL - terminate immediately
  - SIGTERM - request termination
  - SIGCHLD - child status changed
- [ ] File descriptors:
  - Per-process FD table
  - stdin (0), stdout (1), stderr (2)
  - Pipe endpoints as FDs

**Success Test:**
- Producer/consumer via pipe
- `kill` terminates process
- SIGCHLD delivered on child exit

**Files to Create:**
- `include/pipe.h` - pipe structures
- `src/lib/pipe.c` - pipe implementation
- `include/signal.h` - signal definitions
- `src/lib/signal.c` - signal handling

---

## Estimated Progress Checkpoints (Updated)

- **After M2:** Can demonstrate boot + input
- **After M4:** First "useful" state (saves data)
- **After M6:** True standalone kernel
- **After M8:** Core Chrono vision realized (time travel)
- **After M12:** Daily driver candidate (reliability)
- **After M14:** Memory management foundation
- **After M15:** Chrono-native timeline system working
- **After M17:** Multiple execution contexts with context switching
- **After M18:** Preemptive multitasking OS ✓ ACHIEVED
- **After M21:** Can run user programs
- **After M23:** Full process model with IPC

---

## Success Metrics (Updated)

| Milestone | Key Metric | Status |
|-----------|------------|--------|
| M1 | Text visible on Aorus X3 screen | ✓ DONE |
| M2 | Can type and see response | ✓ DONE |
| M3 | `disk` shows both drives | ✓ DONE |
| M4 | Data persists across reboot | ✓ DONE |
| M5 | Kernel runs, keyboard works | ✓ DONE |
| M6 | Timer ticks, interrupts work | ✓ DONE |
| M7 | Deduplication verified | ✓ DONE |
| M8 | Time travel works | ✓ DONE |
| M9 | Files and directories work | ✓ DONE |
| M10 | USB log saved (optional) | SKIPPED |
| M11 | History and completion work | ✓ DONE |
| M12 | No data loss under stress | ✓ DONE |
| M14 | PMM/VMM/Heap working | ✓ DONE |
| M15 | Timeline commands work in kernel | ✓ DONE |
| M16 | `ps` shows multiple tasks | ✓ DONE |
| M17 | `yield` switches tasks | ✓ DONE |
| M18 | Preemptive scheduling works | ✓ DONE |
| M19 | Code runs in ring 3 | ✓ DONE |
| M20 | Syscalls work | PENDING |
| M21 | ELF binary executes | PENDING |
| M22 | fork/wait work | PENDING |
| M23 | Pipes and signals work | PENDING |

---

# THE DRIVER PHILOSOPHY

## Core Vision

> *"The user drives. The system maintains."*

Chrono OS aspires to be like a perfect car: the driver thinks only about the destination, never about oil pressure, fuel mixture, or error recovery. The system handles everything invisibly.

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTENT LAYER                              │
│  Where the user lives. Goals, desires, outcomes.                 │
│  "Find what I was working on Tuesday"                           │
│  Language: Outcomes, not operations                              │
│  ← The user ONLY operates here                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NAVIGATION LAYER                            │
│  Where Chrono interprets and steers                              │
│  Translates intent → action, anticipates needs, corrects course │
│  Visibility: On request only ("explain", "show forks")           │
│  ← Visible only when user chooses to look                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MAINTENANCE LAYER                            │
│  Where the engine runs (TSS, drivers, memory, I/O)              │
│  "Sector write failed → retry with different timing"            │
│  Visibility: NEVER, unless explicitly requested via diagnostics │
│  ← NEVER visible unless user explicitly opens the hood          │
└─────────────────────────────────────────────────────────────────┘
```

## Cultural Foundations

| Philosophy | Meaning | In Chrono |
|------------|---------|-----------|
| **Ma (間)** | Japanese negative space | 97% of screen is meaningful emptiness |
| **Wabi-Sabi (侘寂)** | Beauty in imperfection | Errors are preserved as forks, not hidden |
| **Sprezzatura** | Studied carelessness | Complex work appears effortless |
| **Yūgen (幽玄)** | Profound mystery | Hidden depths for explorers |

## Error Philosophy

```
TRADITIONAL OS:  Error dialog → User decides → Anxiety
CHRONO OS:       Error detected → Fork created → Silent recovery → User continues
```

| Error Class | Handler | User Sees |
|-------------|---------|-----------|
| Transient | Maintenance | Nothing |
| Recoverable | Navigation | Maybe brief delay |
| Degradable | Navigation | Feature unavailable |
| Safety | Intent | Clear, non-technical explanation |

---

## Phase 12: Maintenance Layer Polish (M24-M25)

*Refine the engine compartment before building the user experience*

### M24: Silent Error Recovery
**Goal:** All recoverable errors handled invisibly

**Deliverables:**
- [ ] Error classification system (transient, recoverable, degradable, safety)
- [ ] Automatic retry with backoff for I/O errors
- [ ] Fork creation on error for forensics
- [ ] Recovery pattern library:
  - Silent retry (transient I/O)
  - Silent revert (state corruption)
  - Graceful degradation (subsystem unavailable)
- [ ] No technical error messages reach user

**Success Test:**
- Simulate disk timeout → system retries, user sees nothing
- Corrupt TSS state → system reverts, fork preserved
- Check `show forks --system` reveals recovery history

### M25: Diagnostic Interface
**Goal:** "Open the hood" capability for power users

**Deliverables:**
- [ ] `diag` command family:
  - `diag` - System health summary
  - `diag storage` - TSS state, block allocation
  - `diag hardware` - Driver states, interrupts
  - `diag memory` - Heap state, allocation patterns
  - `diag log` - Recent Maintenance Layer events
  - `diag forks --system` - System-initiated forks
- [ ] `trace <command>` - Show all layers during execution
- [ ] Diagnostic output uses technical language (appropriate for this layer)

**Success Test:**
- `diag` shows green status for all subsystems
- `diag storage` shows TSS internals
- `trace store hello` shows CAS operations

---

## Phase 13: Navigation Layer (M26-M28)

*Build the intelligent intermediary*

### M26: Intent Classification
**Goal:** Understand what the user is trying to accomplish

**Deliverables:**
- [ ] Intent type enumeration:
  - CREATE, FIND, MODIFY, EXPLORE, RECOVER, UNDERSTAND, COMPARE, SHARE
- [ ] Intent context structure (type, confidence, temporal hints, keywords)
- [ ] Basic intent classifier for shell commands
- [ ] Translate user input to internal operations

**Success Test:**
- "find notes" → classified as INTENT_FIND
- "show changes" → classified as INTENT_COMPARE
- Classification logged but not shown to user

### M27: Attention Model
**Goal:** Understand user engagement level

**Deliverables:**
- [ ] Attention states:
  - DEEP (focused work, minimize interruptions)
  - ACTIVE (working, interruptible)
  - BROWSING (exploring, low commitment)
  - IDLE (present but not engaged)
  - AWAY (user has left)
- [ ] Typing-based flow detection (sustained input = DEEP)
- [ ] Auto-Moment frequency adjusts to attention:
  - DEEP: More frequent (user producing)
  - BROWSING: Less frequent (user consuming)
  - AWAY: Create checkpoint, enter low-power

**Success Test:**
- Sustained typing → system enters "flow mode"
- No input for 5 minutes → checkpoint created automatically

### M28: Trajectory Correction
**Goal:** Silently recover from problems without user awareness

**Deliverables:**
- [ ] Recovery state machine:
  - Normal → Error detected → Classify → Recover → Resume
- [ ] Fork-based forensics (every error creates a fork)
- [ ] Replay valid actions after revert
- [ ] Performance budgets:
  - User feedback: <100ms
  - User completion: <1000ms
  - User patience: <5000ms
- [ ] Only surface to Intent Layer if truly unrecoverable

**Success Test:**
- Corrupt data mid-operation → system reverts, replays, continues
- User never sees error, but fork exists for debugging

---

## Phase 14: Intent Layer (M29-M31)

*Build the user's world*

### M29: Natural Language Interface
**Goal:** Users express goals, not commands

**Deliverables:**
- [ ] Natural query parser:
  - "What was I working on Tuesday?" → temporal search
  - "Find the budget email" → content search
  - "Show what changed" → diff last two moments
- [ ] Response in outcome language (never technical)
- [ ] Context-aware responses (remember conversation)

**Success Test:**
- "What changed?" → "You modified the introduction and added a conclusion"
- "Find that thing from last week" → Relevant moment displayed

### M30: Activity Spaces
**Goal:** Visual atmosphere reflects user's mental state

**Deliverables:**
- [ ] Activity detection:
  - Idle/Home (deep void, blue-violet nebulae)
  - Writing (warm brown atmosphere)
  - Timeline (purple-violet atmosphere)
  - Media (pure black)
- [ ] Subtle 2-second color transitions
- [ ] Nebulae (soft gradients at 12% opacity, blur 80px)
- [ ] 97% meaningful emptiness principle

**Colors:**
| Activity | Background | Nebulae |
|----------|------------|---------|
| Idle | `#050506` | Blue-violet |
| Writing | `#1a150d` | Warm amber |
| Timeline | `#100c1a` | Purple |
| Media | `#000000` | None |

**Success Test:**
- Start writing → atmosphere warms over 2 seconds
- Switch to timeline → purple tint appears
- User feels the shift, doesn't consciously notice

### M31: True Elegance UI
**Goal:** Minimal, beautiful interface

**Deliverables:**
- [ ] 97% screen is meaningful emptiness
- [ ] User's focus occupies ~3% of screen
- [ ] Elements appear only when serving intent
- [ ] No status bars, no progress indicators (unless truly needed)
- [ ] No confirmation dialogs for reversible actions
- [ ] Delete is instant (it's just a past Moment)

**Success Test:**
- Delete a file → no confirmation, instant
- "undo" → file returns from its Moment
- Screen feels calm, spacious, focused

---

## Phase 15: Presence Layer (M32-M34) - Future Vision

*Beyond input: the system perceives the user*

### M32: Typing-Based Presence
**Goal:** Detect flow state from keyboard patterns

**Deliverables:**
- [ ] Typing velocity tracking
- [ ] Sustained typing detection (8+ seconds = flow)
- [ ] Presence indicator (subtle dot: gray → gold in flow)
- [ ] System behavior adjusts:
  - Flow: UI minimizes, haptics silent, notifications queued
  - Idle: Preserve state aggressively

### M33: Visual Presence (Requires Webcam)
**Goal:** System sees user attention

**Deliverables:**
- [ ] Face detection (present/away)
- [ ] Gaze tracking (on screen/looking away)
- [ ] Expression recognition (focused, confused, relaxed)
- [ ] All processing local, no recording, frames discarded
- [ ] Graceful fallback without camera

**System responses:**
- Eyes away → pause animations, preserve state
- Focused expression → maximum invisibility
- Confused expression → surface help cues subtly
- User returned → "Welcome back" + restore context

### M34: Haptic Communication
**Goal:** System communicates through touch

**Deliverables:**
- [ ] Haptic vocabulary:
  - Moment captured: single pulse (30ms)
  - Protection activated: wave pattern (50-30-50ms)
  - Welcome back: warm pulse (20-40-60ms)
  - Flow recognized: haptics go silent
- [ ] Visual fallback for non-haptic devices
- [ ] Haptics feel like "trusted companion's hand on shoulder"

---

## Updated Progress Checkpoints

- **After M12:** Daily driver candidate (reliability)
- **After M17:** Multiple execution contexts (current milestone)
- **After M23:** Full process model with IPC
- **After M25:** Maintenance Layer complete (invisible engine)
- **After M28:** Navigation Layer complete (intelligent steering)
- **After M31:** Intent Layer complete (user's world)
- **After M34:** Presence Layer complete (system perceives user)

---

## Updated Success Metrics

| Milestone | Key Metric | Status |
|-----------|------------|--------|
| M1-M16 | Foundation milestones | ✓ DONE |
| M17 | `yield` switches tasks | ✓ DONE |
| M18-M23 | Process model complete | PENDING |
| M24 | Errors recover silently | PENDING |
| M25 | `diag` shows internals | PENDING |
| M26 | Intent classification works | PENDING |
| M27 | Attention model adjusts behavior | PENDING |
| M28 | Trajectory correction invisible | PENDING |
| M29 | Natural language queries work | PENDING |
| M30 | Activity spaces shift atmosphere | PENDING |
| M31 | 97% meaningful emptiness | PENDING |
| M32 | Typing-based flow detection | PENDING |
| M33 | Visual presence awareness | PENDING |
| M34 | Haptic communication works | PENDING |

---

## The Ultimate Test

When Chrono OS is complete:

```
You sit down.
The screen awakens—not because you touched anything,
but because it saw you.

Your work from yesterday appears, right where you left it.
The atmosphere shifts to warm brown. Writing mode.

You start typing. The interface fades to almost nothing.
Just you and your words. The system recognized flow.

Something fails underneath—a storage hiccup.
You feel the faintest pulse in the device. Warmth.
"I handled it." You didn't consciously notice.

You never gave a command.
You never clicked anything.
You just... worked.

The system was present with you the entire time.
```

---

*"Ship early, ship often. Each milestone is a working system."*

*"The user drives. The system maintains."*
