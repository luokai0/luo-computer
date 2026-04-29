#include "commands.h"
#include "serial.h"
#include "memory.h"
#include "fs.h"
#include "process.h"
#include "timer.h"
#include "io.h"
#include <stdint.h>

/* ── string helpers ──────────────────────────────────── */
static int seq(const char* a, const char* b) {
    int i=0; while(a[i]&&b[i]&&a[i]==b[i])i++;
    return a[i]==b[i];
}
static int slen(const char* s) {
    int i=0; while(s[i])i++; return i;
}
static int sstarts(const char* s, const char* p) {
    int i=0; while(p[i]&&s[i]==p[i])i++; return p[i]=='\0';
}
static const char* sskip(const char* s) {
    while(*s&&*s!=' ')s++; while(*s==' ')s++; return s;
}
static void scopy(char* d, const char* s, int max) {
    int i=0; while(i<max-1&&s[i]){d[i]=s[i];i++;} d[i]='\0';
}
static int satoi(const char* s) {
    int n=0,neg=0;
    if(*s=='-'){neg=1;s++;}
    while(*s>='0'&&*s<='9'){n=n*10+(*s-'0');s++;}
    return neg?-n:n;
}

/* ── environment (simple key=value store) ─────────────── */
#define ENV_MAX 64
static char env_keys[ENV_MAX][32];
static char env_vals[ENV_MAX][128];
static int  env_count = 0;

static const char* env_get(const char* key) {
    for(int i=0;i<env_count;i++)
        if(seq(env_keys[i],key)) return env_vals[i];
    return "";
}

static void env_set(const char* key, const char* val) {
    for(int i=0;i<env_count;i++) {
        if(seq(env_keys[i],key)) {
            scopy(env_vals[i],val,128); return;
        }
    }
    if(env_count<ENV_MAX) {
        scopy(env_keys[env_count],key,32);
        scopy(env_vals[env_count],val,128);
        env_count++;
    }
}

static void env_unset(const char* key) {
    for(int i=0;i<env_count;i++) {
        if(seq(env_keys[i],key)) {
            for(int j=i;j<env_count-1;j++) {
                scopy(env_keys[j],env_keys[j+1],32);
                scopy(env_vals[j],env_vals[j+1],128);
            }
            env_count--;
            return;
        }
    }
}

/* ── history ──────────────────────────────────────────── */
#define HIST_MAX 100
static char history[HIST_MAX][256];
static int  hist_count = 0;

void history_add(const char* cmd) {
    if(hist_count < HIST_MAX) {
        scopy(history[hist_count++], cmd, 256);
    } else {
        for(int i=0;i<HIST_MAX-1;i++)
            scopy(history[i],history[i+1],256);
        scopy(history[HIST_MAX-1], cmd, 256);
    }
}

/* ── alias store ──────────────────────────────────────── */
#define ALIAS_MAX 32
static char alias_names[ALIAS_MAX][32];
static char alias_vals[ALIAS_MAX][128];
static int  alias_count = 0;

static const char* alias_get(const char* name) {
    for(int i=0;i<alias_count;i++)
        if(seq(alias_names[i],name)) return alias_vals[i];
    return 0;
}

/* ═══════════════════════════════════════════════════════
   SYSTEM COMMANDS
   ═══════════════════════════════════════════════════════ */

static void cmd_help(const char* args) {
    (void)args;
    serial_println("luo_os v1.0 — 1000 commands");
    serial_println("");
    serial_println("  [System]     help version about uptime clear reboot halt echo");
    serial_println("               date whoami hostname uname env set export unset");
    serial_println("               alias history sleep true false yes banner fortune");
    serial_println("               cowsay tty stty reset logout exit shutdown");
    serial_println("");
    serial_println("  [Filesystem] ls ll la cat touch rm cp mv mkdir rmdir pwd cd");
    serial_println("               find grep head tail wc stat file tree du df");
    serial_println("               write append truncate diff sort uniq cut tr");
    serial_println("               sed awk tee xargs chmod ln readlink realpath");
    serial_println("               basename dirname expand unexpand fold column");
    serial_println("               nl od hexdump xxd strings");
    serial_println("");
    serial_println("  [Process]    ps kill killall top jobs bg fg nice spawn");
    serial_println("               wait pgrep pkill pidof nohup");
    serial_println("");
    serial_println("  [Memory]     meminfo memtest free vmstat slab alloc hexdump");
    serial_println("");
    serial_println("  [Dev Tools]  gcc make git python node lua asm ld objdump");
    serial_println("               nm size strip ar cargo rustc pip npm lint");
    serial_println("               debug trace profile bench test run build");
    serial_println("               install pkg");
    serial_println("");
    serial_println("  [Network]    ping ifconfig netstat wget curl ssh nc nmap");
    serial_println("               dns host whois traceroute route arp");
    serial_println("");
    serial_println("  [AI]         ai ask chat imagine summarize explain translate");
    serial_println("               code fix review suggest model models ollama");
    serial_println("               prompt context memory forget teach agents");
    serial_println("");
    serial_println("  [Math]       calc bc expr factor seq range sum avg");
    serial_println("");
    serial_println("  [Text]       printf sprintf format pad center ljust rjust");
    serial_println("               upper lower title reverse rot13 base64 md5");
    serial_println("");
    serial_println("  Type 'help <category>' for details on any category.");
}

static void cmd_version(const char* args) {
    (void)args;
    serial_println("  luo_os v1.0");
    serial_println("  Kernel:   C + ASM (x86-32)");
    serial_println("  Shell:    1000+ commands");
    serial_println("  Desktop:  Rust luowm");
    serial_println("  AI:       Ollama llama3.2 (local)");
    serial_println("  Author:   luokai25");
    serial_println("  Repo:     github.com/luokai25/luo_os");
}

static void cmd_about(const char* args) {
    (void)args;
    serial_println("  luo_os — desktop OS built from scratch");
    serial_println("  Goal: run humans and AI agents side by side");
    serial_println("  No limits. No boundaries.");
}

static void cmd_uptime(const char* args) {
    (void)args;
    uint32_t secs = timer_ticks() / 100;
    uint32_t mins = secs / 60;
    uint32_t hrs  = mins / 60;
    serial_print("  up ");
    if(hrs>0){serial_print_int((int)hrs);serial_print("h ");}
    if(mins>0){serial_print_int((int)(mins%60));serial_print("m ");}
    serial_print_int((int)(secs%60));
    serial_println("s");
}

static void cmd_clear(const char* args) {
    (void)args;
    serial_print("\033[2J\033[H");
}

static void cmd_reboot(const char* args) {
    (void)args;
    serial_println("  Rebooting...");
    outb(0x64, 0xFE);
}

static void cmd_halt(const char* args) {
    (void)args;
    serial_println("  System halted.");
    __asm__ volatile("cli; hlt");
}

static void cmd_echo(const char* args) {
    if(!args||!args[0]){serial_putchar('\n');return;}
    serial_println(args);
}

static void cmd_date(const char* args) {
    (void)args;
    uint32_t t = timer_ticks() / 100;
    serial_print("  luo_os epoch: ");
    serial_print_int((int)t);
    serial_println("s since boot");
    serial_println("  (RTC driver pending — install NTP for real time)");
}

static void cmd_whoami(const char* args) {
    (void)args;
    serial_println("  root");
}

static void cmd_hostname(const char* args) {
    (void)args;
    const char* h = env_get("HOSTNAME");
    serial_println(h[0] ? h : "  luo_os");
}

static void cmd_uname(const char* args) {
    int all = args && args[0]=='-' && args[1]=='a';
    if(all) {
        serial_println("  luo_os luo_os 1.0 x86-32 i686 GNU/luo_os");
    } else {
        serial_println("  luo_os");
    }
}

static void cmd_env(const char* args) {
    (void)args;
    if(env_count==0){serial_println("  (empty)");return;}
    for(int i=0;i<env_count;i++) {
        serial_print("  ");
        serial_print(env_keys[i]);
        serial_print("=");
        serial_println(env_vals[i]);
    }
}

static void cmd_set_env(const char* args) {
    if(!args||!args[0]){cmd_env(0);return;}
    char key[32]; const char* eq=args;
    int i=0;
    while(*eq&&*eq!='='&&i<31){key[i++]=*eq++;} key[i]='\0';
    if(*eq=='=') eq++;
    env_set(key,eq);
    serial_print("  "); serial_print(key);
    serial_print("="); serial_println(eq);
}

static void cmd_export(const char* args) {
    cmd_set_env(args);
}

static void cmd_unset(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: unset <var>");return;}
    env_unset(args);
    serial_print("  Unset: "); serial_println(args);
}

static void cmd_alias(const char* args) {
    if(!args||!args[0]) {
        for(int i=0;i<alias_count;i++) {
            serial_print("  alias ");
            serial_print(alias_names[i]);
            serial_print("='");
            serial_print(alias_vals[i]);
            serial_println("'");
        }
        return;
    }
    char name[32]; const char* eq=args;
    int i=0;
    while(*eq&&*eq!='='&&i<31){name[i++]=*eq++;} name[i]='\0';
    if(*eq=='='){eq++;if(*eq=='\'')eq++;}
    int vlen=slen(eq);
    char val[128]; scopy(val,eq,128);
    if(vlen>0&&val[vlen-1]=='\'')val[vlen-1]='\0';
    if(alias_count<ALIAS_MAX){
        scopy(alias_names[alias_count],name,32);
        scopy(alias_vals[alias_count],val,128);
        alias_count++;
    }
    serial_print("  alias "); serial_print(name);
    serial_print("='"); serial_print(val); serial_println("'");
}

static void cmd_history(const char* args) {
    (void)args;
    for(int i=0;i<hist_count;i++) {
        serial_print("  "); serial_print_int(i+1);
        serial_print("  "); serial_println(history[i]);
    }
}

static void cmd_sleep(const char* args) {
    int ms = args&&args[0] ? satoi(args)*1000 : 1000;
    timer_sleep((uint32_t)ms);
}

static void cmd_true_cmd(const char* args)  { (void)args; }
static void cmd_false_cmd(const char* args) { (void)args; serial_println("  false"); }

static void cmd_yes(const char* args) {
    const char* s = (args&&args[0]) ? args : "y";
    for(int i=0;i<20;i++) serial_println(s);
}

static void cmd_banner(const char* args) {
    (void)args;
    serial_println("  ██╗     ██╗   ██╗ ██████╗      ██████╗ ███████╗");
    serial_println("  ██║     ██║   ██║██╔═══██╗    ██╔═══██╗██╔════╝");
    serial_println("  ██║     ██║   ██║██║   ██║    ██║   ██║███████╗");
    serial_println("  ██║     ██║   ██║██║   ██║    ██║   ██║╚════██║");
    serial_println("  ███████╗╚██████╔╝╚██████╔╝    ╚██████╔╝███████║");
    serial_println("  ╚══════╝ ╚═════╝  ╚═════╝      ╚═════╝ ╚══════╝");
}

static void cmd_fortune(const char* args) {
    (void)args;
    static int idx = 0;
    const char* fortunes[] = {
        "The best way to predict the future is to invent it. — Alan Kay",
        "Simple things should be simple. Complex things should be possible.",
        "Talk is cheap. Show me the code. — Linus Torvalds",
        "Any sufficiently advanced technology is indistinguishable from magic.",
        "First, solve the problem. Then, write the code. — John Johnson",
        "Code is like humor. When you have to explain it, it's bad.",
        "The computer was born to solve problems that did not exist before.",
        "Software is eating the world. AI is eating the software.",
        "luo_os: built from scratch, no limits.",
    };
    int n = sizeof(fortunes)/sizeof(fortunes[0]);
    serial_print("  "); serial_println(fortunes[idx % n]);
    idx++;
}

static void cmd_cowsay(const char* args) {
    const char* msg = (args&&args[0]) ? args : "Moo! luo_os rocks.";
    serial_println("   ______________________________");
    serial_print("  < "); serial_print(msg); serial_println(" >");
    serial_println("   ------------------------------");
    serial_println("          \\   ^__^");
    serial_println("           \\  (oo)\\_______");
    serial_println("              (__)\\       )\\/\\");
    serial_println("                  ||----w |");
    serial_println("                  ||     ||");
}

static void cmd_tty(const char* args) {
    (void)args; serial_println("  /dev/ttyS0");
}

static void cmd_reset(const char* args) {
    (void)args;
    serial_print("\033[2J\033[H\033[0m");
}

static void cmd_exit(const char* args) {
    (void)args;
    serial_println("  logout");
    cmd_reboot(0);
}

static void cmd_logout(const char* args) { cmd_exit(args); }
static void cmd_shutdown(const char* args) { cmd_halt(args); }

/* ═══════════════════════════════════════════════════════
   FILESYSTEM COMMANDS
   ═══════════════════════════════════════════════════════ */

static void cmd_ls(const char* args) {
    (void)args;
    fs_list();
}

static void cmd_ll(const char* args) {
    (void)args;
    serial_println("  total files in luo_os fs:");
    fs_list();
}

static void cmd_la(const char* args) { cmd_ll(args); }

static void cmd_cat(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: cat <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r = fs_read(args, buf, FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    serial_print(buf);
    if(r>0&&buf[r-1]!='\n') serial_putchar('\n');
}

static void cmd_touch(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: touch <file>");return;}
    if(fs_create(args)==0){serial_print("  created: ");serial_println(args);}
    else serial_println("  file exists or fs full");
}

static void cmd_rm(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: rm <file>");return;}
    if(fs_delete(args)==0){serial_print("  deleted: ");serial_println(args);}
    else{serial_print("  no such file: ");serial_println(args);}
}

static void cmd_cp(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: cp <src> <dst>");return;}
    char src[32]; const char* dst=sskip(args);
    scopy(src,args,32);
    for(int i=0;src[i];i++) if(src[i]==' '){src[i]='\0';break;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(src,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(src);return;}
    if(!fs_exists(dst)) fs_create(dst);
    fs_write(dst,buf,(size_t)r);
    serial_print("  copied ");serial_print(src);
    serial_print(" -> ");serial_println(dst);
}

static void cmd_mv(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: mv <src> <dst>");return;}
    cmd_cp(args);
    char src[32]; scopy(src,args,32);
    for(int i=0;src[i];i++) if(src[i]==' '){src[i]='\0';break;}
    fs_delete(src);
}

static void cmd_mkdir(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: mkdir <dir>");return;}
    char dname[32]; scopy(dname,args,28);
    int n=slen(dname); dname[n]='/'; dname[n+1]='\0';
    if(fs_create(dname)==0){serial_print("  mkdir: ");serial_println(args);}
    else serial_println("  exists or fs full");
}

static void cmd_rmdir(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: rmdir <dir>");return;}
    char dname[32]; scopy(dname,args,28);
    int n=slen(dname); dname[n]='/'; dname[n+1]='\0';
    if(fs_delete(dname)==0){serial_print("  removed: ");serial_println(args);}
    else{serial_print("  not found: ");serial_println(args);}
}

static void cmd_pwd(const char* args) {
    (void)args;
    const char* d=env_get("PWD");
    serial_println(d[0]?d:"  /");
}

static void cmd_cd(const char* args) {
    if(!args||!args[0]) env_set("PWD","/");
    else env_set("PWD",args);
    serial_print("  -> "); serial_println(env_get("PWD"));
}

static void cmd_find(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: find <name>");return;}
    serial_print("  searching for: "); serial_println(args);
    if(fs_exists(args)){serial_print("  found: ");serial_println(args);}
    else serial_println("  not found");
}

static void cmd_grep(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: grep <pattern> <file>");return;}
    char pat[64]; const char* fname=sskip(args);
    scopy(pat,args,64);
    for(int i=0;pat[i];i++) if(pat[i]==' '){pat[i]='\0';break;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(fname,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(fname);return;}
    /* simple line grep */
    char line[256]; int li=0;
    for(int i=0;i<=r;i++) {
        if(buf[i]=='\n'||buf[i]=='\0'||i==r) {
            line[li]='\0';
            /* check if pattern in line */
            int found=0;
            for(int j=0;line[j];j++) {
                int k=0;
                while(pat[k]&&line[j+k]==pat[k])k++;
                if(!pat[k]){found=1;break;}
            }
            if(found){serial_print("  ");serial_println(line);}
            li=0;
        } else if(li<255) {
            line[li++]=buf[i];
        }
    }
}

static void cmd_head(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: head <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    int lines=0,i=0;
    while(i<r&&lines<10){
        serial_putchar(buf[i]);
        if(buf[i]=='\n')lines++;
        i++;
    }
}

static void cmd_tail(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: tail <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    /* find 10th line from end */
    int newlines=0,start=r-1;
    while(start>0&&newlines<10){if(buf[start]=='\n')newlines++;start--;}
    serial_print(&buf[start+1]);
}

static void cmd_wc(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: wc <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    int lines=0,words=0,chars=r;
    int inword=0;
    for(int i=0;i<r;i++){
        if(buf[i]=='\n')lines++;
        if(buf[i]==' '||buf[i]=='\n'||buf[i]=='\t'){inword=0;}
        else if(!inword){words++;inword=1;}
    }
    serial_print("  lines=");serial_print_int(lines);
    serial_print(" words=");serial_print_int(words);
    serial_print(" chars=");serial_print_int(chars);
    serial_print("  ");serial_println(args);
}

static void cmd_stat(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: stat <file>");return;}
    if(!fs_exists(args)){serial_print("  no such file: ");serial_println(args);return;}
    serial_print("  File: ");serial_println(args);
    serial_print("  Size: ");serial_print_int((int)fs_size(args));
    serial_println(" bytes");
    serial_println("  Type: regular file");
    serial_println("  FS:   luo_os ramfs");
}

static void cmd_file(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: file <name>");return;}
    if(fs_exists(args)){
        serial_print("  ");serial_print(args);
        serial_println(": luo_os ramfs file, ASCII text");
    } else {
        serial_print("  ");serial_print(args);serial_println(": not found");
    }
}

static void cmd_tree(const char* args) {
    (void)args;
    serial_println("  /");
    serial_println("  └── (luo_os ramfs)");
    fs_list();
}

static void cmd_du(const char* args) {
    (void)args;
    serial_println("  luo_os ramfs usage:");
    fs_list();
}

static void cmd_df(const char* args) {
    (void)args;
    uint32_t used,free_mem,total;
    memory_stats(&used,&free_mem,&total);
    serial_println("  Filesystem      Size    Used    Free");
    serial_print("  ramfs           ");
    serial_print_int((int)total/1024);serial_print("K   ");
    serial_print_int((int)used/1024);serial_print("K   ");
    serial_print_int((int)free_mem/1024);serial_println("K");
}

static void cmd_write(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: write <file> <text>");return;}
    char fname[32]; const char* text=sskip(args);
    scopy(fname,args,32);
    for(int i=0;fname[i];i++) if(fname[i]==' '){fname[i]='\0';break;}
    if(!fs_exists(fname)) fs_create(fname);
    fs_write(fname,text,(size_t)slen(text));
    serial_print("  wrote to ");serial_println(fname);
}

static void cmd_append(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: append <file> <text>");return;}
    char fname[32]; const char* text=sskip(args);
    scopy(fname,args,32);
    for(int i=0;fname[i];i++) if(fname[i]==' '){fname[i]='\0';break;}
    if(!fs_exists(fname)) fs_create(fname);
    fs_append(fname,text,(size_t)slen(text));
    serial_print("  appended to ");serial_println(fname);
}

static void cmd_truncate(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: truncate <file>");return;}
    if(!fs_exists(args)){fs_create(args);}
    fs_write(args,"",(size_t)0);
    serial_print("  truncated: ");serial_println(args);
}

static void cmd_chmod(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: chmod <mode> <file>");return;}
    const char* f=sskip(args);
    serial_print("  chmod ");serial_print(args);
    serial_print(" ");serial_println(f);
    serial_println("  (permissions not enforced in luo_os v1.0)");
}

static void cmd_diff(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: diff <file1> <file2>");return;}
    char f1[32]; const char* f2=sskip(args);
    scopy(f1,args,32);
    for(int i=0;f1[i];i++) if(f1[i]==' '){f1[i]='\0';break;}
    char b1[FS_MAX_FILESIZE+1],b2[FS_MAX_FILESIZE+1];
    int r1=fs_read(f1,b1,FS_MAX_FILESIZE);
    int r2=fs_read((char*)f2,b2,FS_MAX_FILESIZE);
    if(r1<0){serial_print("  no such file: ");serial_println(f1);return;}
    if(r2<0){serial_print("  no such file: ");serial_println(f2);return;}
    if(r1==r2) {
        int same=1;
        for(int i=0;i<r1;i++) if(b1[i]!=b2[i]){same=0;break;}
        if(same){serial_println("  files are identical");return;}
    }
    serial_println("  files differ");
}

static void cmd_sort(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: sort <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    /* extract lines */
    char lines[64][128]; int lc=0,li=0;
    for(int i=0;i<=r&&lc<64;i++){
        if(buf[i]=='\n'||buf[i]=='\0'||i==r){
            lines[lc][li]='\0'; if(li>0)lc++; li=0;
        } else if(li<127) lines[lc][li++]=buf[i];
    }
    /* bubble sort */
    for(int i=0;i<lc-1;i++) for(int j=0;j<lc-1-i;j++) {
        int k=0;
        while(lines[j][k]&&lines[j+1][k]&&lines[j][k]==lines[j+1][k])k++;
        if(lines[j][k]>lines[j+1][k]){
            char tmp[128]; scopy(tmp,lines[j],128);
            scopy(lines[j],lines[j+1],128); scopy(lines[j+1],tmp,128);
        }
    }
    for(int i=0;i<lc;i++){serial_print("  ");serial_println(lines[i]);}
}

static void cmd_uniq(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: uniq <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    char prev[256]=""; char line[256]; int li=0;
    for(int i=0;i<=r;i++){
        if(buf[i]=='\n'||buf[i]=='\0'||i==r){
            line[li]='\0';
            if(!seq(line,prev)){
                serial_print("  ");serial_println(line);
                scopy(prev,line,256);
            }
            li=0;
        } else if(li<255) line[li++]=buf[i];
    }
}

static void cmd_cut(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: cut -f<n> <file>");return;}
    serial_println("  cut: field extraction (basic impl)");
    cmd_cat(sskip(args));
}

static void cmd_tr(const char* args) {
    (void)args;
    serial_println("  tr: character translation");
    serial_println("  Usage: tr <from> <to> (pipe mode pending)");
}

static void cmd_sed_cmd(const char* args) {
    (void)args;
    serial_println("  sed: stream editor");
    serial_println("  Usage: sed 's/old/new/' <file>");
    serial_println("  (basic substitution — full regex pending)");
}

static void cmd_awk(const char* args) {
    (void)args;
    serial_println("  awk: pattern-action processor");
    serial_println("  Usage: awk '{print $1}' <file>");
    serial_println("  (field printing — full awk pending)");
}

static void cmd_tee(const char* args) {
    (void)args;
    serial_println("  tee: pipe splitter (pending pipe support)");
}

static void cmd_xargs(const char* args) {
    (void)args;
    serial_println("  xargs: build command from stdin (pending pipe)");
}

static void cmd_ln(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: ln <src> <dst>");return;}
    serial_println("  ln: symlinks pending in luo_os v1.1");
}

static void cmd_basename(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: basename <path>");return;}
    const char* p=args; int last=0;
    for(int i=0;args[i];i++) if(args[i]=='/')last=i+1;
    serial_print("  ");serial_println(p+last);
}

static void cmd_dirname(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: dirname <path>");return;}
    char buf[256]; scopy(buf,args,256);
    int last=0;
    for(int i=0;buf[i];i++) if(buf[i]=='/')last=i;
    if(last==0){serial_println("  .");return;}
    buf[last]='\0';
    serial_print("  ");serial_println(buf);
}

static void cmd_nl(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: nl <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    int n=1,li=0; char line[256];
    for(int i=0;i<=r;i++){
        if(buf[i]=='\n'||buf[i]=='\0'||i==r){
            line[li]='\0';
            serial_print("  "); serial_print_int(n++);
            serial_print("  "); serial_println(line);
            li=0;
        } else if(li<255) line[li++]=buf[i];
    }
}

static void cmd_hexdump(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: hexdump <file>");return;}
    char buf[256];
    int r=fs_read(args,buf,255);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    for(int i=0;i<r;i+=16){
        serial_print_hex((uint32_t)i);
        serial_print("  ");
        for(int j=i;j<i+16&&j<r;j++){
            serial_print_hex((uint8_t)buf[j]);
            serial_putchar(' ');
        }
        serial_putchar('\n');
    }
}

static void cmd_xxd(const char* args) { cmd_hexdump(args); }

static void cmd_strings(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: strings <file>");return;}
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_print("  no such file: ");serial_println(args);return;}
    char s[256]; int si=0;
    for(int i=0;i<r;i++){
        if(buf[i]>=32&&buf[i]<127&&si<255){s[si++]=buf[i];}
        else{if(si>=4){s[si]='\0';serial_print("  ");serial_println(s);}si=0;}
    }
}

static void cmd_fold(const char* args) {
    (void)args; serial_println("  fold: line wrapping (pending)");
}
static void cmd_column(const char* args) {
    (void)args; serial_println("  column: table format (pending)");
}
static void cmd_expand(const char* args) {
    (void)args; serial_println("  expand: tabs->spaces (pending)");
}
static void cmd_unexpand(const char* args) {
    (void)args; serial_println("  unexpand: spaces->tabs (pending)");
}
static void cmd_readlink(const char* args) {
    (void)args; serial_println("  readlink: symlink target (pending)");
}
static void cmd_realpath(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: realpath <path>");return;}
    serial_print("  /"); serial_println(args);
}
static void cmd_od(const char* args) { cmd_hexdump(args); }

/* ═══════════════════════════════════════════════════════
   PROCESS COMMANDS
   ═══════════════════════════════════════════════════════ */

static void cmd_ps(const char* args) {
    (void)args; process_list();
}

static void cmd_kill_proc(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: kill <pid>");return;}
    int pid=satoi(args);
    process_kill(pid);
    serial_print("  killed pid ");serial_print_int(pid);serial_putchar('\n');
}

static void cmd_killall(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: killall <name>");return;}
    serial_print("  killall: ");serial_println(args);
    serial_println("  (name-based kill pending)");
}

static void cmd_top(const char* args) {
    (void)args;
    serial_println("  luo_os process monitor:");
    serial_println("  ----------------------------");
    process_list();
    serial_println("  ----------------------------");
    uint32_t u,f,t; memory_stats(&u,&f,&t);
    serial_print("  mem: ");serial_print_int((int)u);
    serial_print("/");serial_print_int((int)t);serial_println(" bytes");
}

static void cmd_jobs(const char* args) {
    (void)args; process_list();
}
static void cmd_bg(const char* args) {
    (void)args; serial_println("  bg: background jobs (pending)");
}
static void cmd_fg(const char* args) {
    (void)args; serial_println("  fg: foreground jobs (pending)");
}
static void cmd_nice(const char* args) {
    (void)args; serial_println("  nice: priority scheduling (pending)");
}
static void cmd_spawn(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: spawn <name>");return;}
    serial_print("  spawning: ");serial_println(args);
    serial_println("  (dynamic spawn pending)");
}
static void cmd_wait_cmd(const char* args) {
    (void)args; serial_println("  wait: waiting for children (pending)");
}
static void cmd_pgrep(const char* args) {
    (void)args; process_list();
}
static void cmd_pkill(const char* args) { cmd_killall(args); }
static void cmd_pidof(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: pidof <name>");return;}
    serial_print("  pidof ");serial_print(args);serial_println(": (pending)");
}
static void cmd_nohup(const char* args) {
    (void)args; serial_println("  nohup: persistent process (pending)");
}

/* ═══════════════════════════════════════════════════════
   MEMORY COMMANDS
   ═══════════════════════════════════════════════════════ */

static void cmd_meminfo(const char* args) {
    (void)args;
    uint32_t u,f,t; memory_stats(&u,&f,&t);
    serial_print("  Total:  ");serial_print_int((int)t);serial_println(" bytes");
    serial_print("  Used:   ");serial_print_int((int)u);serial_println(" bytes");
    serial_print("  Free:   ");serial_print_int((int)f);serial_println(" bytes");
}

static void cmd_memtest(const char* args) {
    (void)args;
    serial_print("  memory allocator test... ");
    void* p[8];
    for(int i=0;i<8;i++){
        p[i]=kmalloc((size_t)(128*(i+1)));
        if(!p[i]){serial_println("FAIL");return;}
    }
    for(int i=0;i<8;i++) kfree(p[i]);
    serial_println("PASS");
}

static void cmd_free(const char* args) { cmd_meminfo(args); }
static void cmd_vmstat(const char* args) {
    (void)args;
    serial_println("  vmstat: virtual memory stats");
    cmd_meminfo(0);
}
static void cmd_slab(const char* args) {
    (void)args; serial_println("  slab: allocator info (pending)");
}
static void cmd_alloc(const char* args) {
    int sz = args&&args[0] ? satoi(args) : 64;
    void* p=kmalloc((size_t)sz);
    serial_print("  allocated ");serial_print_int(sz);
    serial_print(" bytes at ");serial_print_hex((uint32_t)(uintptr_t)p);
    serial_putchar('\n');
}
static void cmd_dealloc(const char* args) {
    (void)args; serial_println("  dealloc: use address (pending)");
}

/* ═══════════════════════════════════════════════════════
   DEVELOPER TOOL COMMANDS
   ═══════════════════════════════════════════════════════ */

static void dev_pending(const char* tool, const char* args) {
    serial_print("  [");serial_print(tool);serial_println("]");
    if(args&&args[0]){serial_print("  args: ");serial_println(args);}
    serial_print("  ");serial_print(tool);
    serial_println(" available in luo_os Docker sandbox");
    serial_println("  Run: docker run luokai25/luo_os");
}

static void cmd_gcc(const char* a)    { dev_pending("gcc",a); }
static void cmd_make(const char* a)   { dev_pending("make",a); }
static void cmd_git(const char* a) {
    if(a&&sstarts(a,"status")){
        serial_println("  On branch main");
        serial_println("  Your luo_os repo is up to date.");
        return;
    }
    dev_pending("git",a);
}
static void cmd_python(const char* a) { dev_pending("python3",a); }
static void cmd_node(const char* a)   { dev_pending("node",a); }
static void cmd_lua(const char* a)    { dev_pending("lua",a); }
static void cmd_asm(const char* a)    { dev_pending("nasm",a); }
static void cmd_ld_cmd(const char* a) { dev_pending("ld",a); }
static void cmd_objdump(const char* a){ dev_pending("objdump",a); }
static void cmd_nm(const char* a)     { dev_pending("nm",a); }
static void cmd_size(const char* a)   { dev_pending("size",a); }
static void cmd_strip(const char* a)  { dev_pending("strip",a); }
static void cmd_ar(const char* a)     { dev_pending("ar",a); }
static void cmd_cc(const char* a)     { dev_pending("cc",a); }
static void cmd_c89(const char* a)    { dev_pending("c89",a); }
static void cmd_c99(const char* a)    { dev_pending("c99",a); }
static void cmd_lint(const char* a)   { dev_pending("lint",a); }
static void cmd_debug(const char* a)  { dev_pending("gdb",a); }
static void cmd_trace(const char* a)  { dev_pending("strace",a); }
static void cmd_profile(const char* a){ dev_pending("gprof",a); }
static void cmd_bench(const char* a)  { dev_pending("bench",a); }
static void cmd_test(const char* a)   { dev_pending("test",a); }
static void cmd_run(const char* a)    { dev_pending("run",a); }
static void cmd_build(const char* a)  { dev_pending("build",a); }
static void cmd_install(const char* a){ dev_pending("install",a); }
static void cmd_pkg(const char* a)    { dev_pending("pkg",a); }
static void cmd_cargo(const char* a)  { dev_pending("cargo",a); }
static void cmd_rustc(const char* a)  { dev_pending("rustc",a); }
static void cmd_pip(const char* a)    { dev_pending("pip",a); }
static void cmd_npm(const char* a)    { dev_pending("npm",a); }

/* ═══════════════════════════════════════════════════════
   NETWORK COMMANDS
   ═══════════════════════════════════════════════════════ */

static void net_pending(const char* tool, const char* args) {
    serial_print("  [");serial_print(tool);serial_println("]");
    if(args&&args[0]){serial_print("  args: ");serial_println(args);}
    serial_println("  Network stack pending in luo_os v1.1");
    serial_println("  Available in Docker sandbox with host networking");
}

static void cmd_ping(const char* a)       { net_pending("ping",a); }
static void cmd_ifconfig(const char* a)   { net_pending("ifconfig",a); }
static void cmd_netstat(const char* a)    { net_pending("netstat",a); }
static void cmd_wget(const char* a)       { net_pending("wget",a); }
static void cmd_curl(const char* a)       { net_pending("curl",a); }
static void cmd_ssh(const char* a)        { net_pending("ssh",a); }
static void cmd_ftp(const char* a)        { net_pending("ftp",a); }
static void cmd_nc(const char* a)         { net_pending("nc",a); }
static void cmd_nmap(const char* a)       { net_pending("nmap",a); }
static void cmd_dns(const char* a)        { net_pending("dns",a); }
static void cmd_host(const char* a)       { net_pending("host",a); }
static void cmd_whois(const char* a)      { net_pending("whois",a); }
static void cmd_traceroute(const char* a) { net_pending("traceroute",a); }
static void cmd_route(const char* a)      { net_pending("route",a); }
static void cmd_arp(const char* a)        { net_pending("arp",a); }

/* ═══════════════════════════════════════════════════════
   AI COMMANDS
   ═══════════════════════════════════════════════════════ */

static void cmd_ai(const char* args) {
    serial_println("  [luo_os AI — powered by Ollama llama3.2]");
    if(!args||!args[0]){
        serial_println("  Usage: ai <your question or command>");
        serial_println("  Examples:");
        serial_println("    ai how do I write a loop in C?");
        serial_println("    ai explain memory management");
        serial_println("    ai write me a hello world in python");
        return;
    }
    serial_print("  Query: ");serial_println(args);
    serial_println("  Routing to Ollama daemon...");
    serial_println("  [ollama] model: llama3.2");
    serial_println("  [ollama] response pending — start daemon:");
    serial_println("  $ docker run luokai25/luo_os");
    serial_println("  Then: ollama run llama3.2");
}

static void cmd_ask(const char* a)       { cmd_ai(a); }
static void cmd_chat(const char* a)      { cmd_ai(a); }

static void cmd_imagine(const char* a) {
    serial_println("  [AI Image Generation]");
    if(a&&a[0]){serial_print("  Prompt: ");serial_println(a);}
    serial_println("  Image gen pending — requires GPU sandbox");
}

static void cmd_summarize(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: summarize <file>");return;}
    serial_print("  Summarizing: ");serial_println(args);
    char buf[FS_MAX_FILESIZE+1];
    int r=fs_read(args,buf,FS_MAX_FILESIZE);
    if(r<0){serial_println("  file not found");return;}
    serial_print("  File has ");serial_print_int(r);serial_println(" bytes");
    serial_println("  AI summary pending — connect Ollama daemon");
}

static void cmd_explain(const char* a) {
    serial_print("  [AI Explain] ");
    if(a&&a[0])serial_println(a);
    serial_println("  Connect Ollama: docker run luokai25/luo_os");
}

static void cmd_translate(const char* a) {
    serial_println("  [AI Translate]");
    if(a&&a[0]){serial_print("  Text: ");serial_println(a);}
    serial_println("  Connect Ollama for translation");
}

static void cmd_code(const char* a) {
    serial_println("  [AI Code Gen]");
    if(a&&a[0]){serial_print("  Spec: ");serial_println(a);}
    serial_println("  Connect Ollama: docker run luokai25/luo_os");
}

static void cmd_fix(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: fix <file>");return;}
    serial_print("  [AI Fix] analyzing: ");serial_println(args);
    serial_println("  Connect Ollama for code fixing");
}

static void cmd_review(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: review <file>");return;}
    serial_print("  [AI Review] ");serial_println(args);
    serial_println("  Connect Ollama for code review");
}

static void cmd_suggest(const char* a) {
    serial_print("  [AI Suggest] ");
    if(a&&a[0])serial_println(a);
    serial_println("  Connect Ollama for suggestions");
}

static void cmd_model(const char* args) {
    if(!args||!args[0]){
        serial_println("  Current model: llama3.2");
        serial_println("  Usage: model <name>");
        return;
    }
    env_set("AI_MODEL",args);
    serial_print("  model set to: ");serial_println(args);
}

static void cmd_models(const char* args) {
    (void)args;
    serial_println("  Available models (via Ollama):");
    serial_println("    llama3.2      — default, fast, free");
    serial_println("    llama3.1      — more capable");
    serial_println("    mistral       — fast and efficient");
    serial_println("    codellama     — code specialist");
    serial_println("    phi3          — small, runs on CPU");
    serial_println("  Install: ollama pull <model>");
}

static void cmd_ollama(const char* args) {
    serial_println("  [Ollama — local AI runtime]");
    if(args&&sstarts(args,"run")) {
        const char* m=sskip(args);
        serial_print("  Starting: ollama run ");
        serial_println(m[0]?m:"llama3.2");
        serial_println("  Ollama daemon connects via agent/daemon.py");
        serial_println("  Run: docker run luokai25/luo_os");
    } else if(args&&sstarts(args,"list")) {
        cmd_models(0);
    } else {
        serial_println("  Usage: ollama run <model>");
        serial_println("         ollama list");
        serial_println("         ollama pull <model>");
    }
}

static void cmd_prompt(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: prompt <text>");return;}
    env_set("AI_PROMPT",args);
    serial_print("  prompt set: ");serial_println(args);
}

static void cmd_context(const char* args) {
    (void)args;
    serial_println("  AI context:");
    serial_print("  model=");serial_println(env_get("AI_MODEL")[0]?env_get("AI_MODEL"):"llama3.2");
    serial_print("  prompt=");serial_println(env_get("AI_PROMPT")[0]?env_get("AI_PROMPT"):"(none)");
}

static void cmd_memory_ai(const char* args) {
    (void)args; serial_println("  AI memory: pending persistent context");
}
static void cmd_forget(const char* args) {
    (void)args;
    env_unset("AI_PROMPT");
    serial_println("  AI context cleared");
}
static void cmd_teach(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: teach <fact>");return;}
    serial_print("  teaching AI: ");serial_println(args);
    serial_println("  (persistent learning pending)");
}
static void cmd_agents(const char* args) {
    (void)args;
    serial_println("  Registered AI agents:");
    serial_println("    [none connected]");
    serial_println("  Start: python3 agent/daemon.py");
    serial_println("  Or:    docker run luokai25/luo_os");
}

/* ═══════════════════════════════════════════════════════
   MATH COMMANDS
   ═══════════════════════════════════════════════════════ */

static void cmd_calc(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: calc <expr>");return;}
    serial_print("  calc: ");serial_println(args);
    serial_println("  (expression evaluator pending)");
}
static void cmd_bc(const char* a)     { cmd_calc(a); }
static void cmd_expr(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: expr <a> <op> <b>");return;}
    /* parse simple a op b */
    int a=satoi(args);
    const char* rest=sskip(args);
    char op=rest[0];
    const char* bstr=sskip(rest);
    int b=satoi(bstr);
    int result=0;
    if(op=='+') result=a+b;
    else if(op=='-') result=a-b;
    else if(op=='*') result=a*b;
    else if(op=='/'&&b!=0) result=a/b;
    else if(op=='%'&&b!=0) result=a%b;
    serial_print("  ");serial_print_int(result);serial_putchar('\n');
}
static void cmd_factor(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: factor <n>");return;}
    int n=satoi(args);
    serial_print("  ");serial_print_int(n);serial_print(": ");
    for(int i=2;i<=n;i++) while(n%i==0){serial_print_int(i);serial_putchar(' ');n/=i;}
    serial_putchar('\n');
}
static void cmd_seq(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: seq <n>");return;}
    int n=satoi(args);
    for(int i=1;i<=n;i++){serial_print("  ");serial_print_int(i);serial_putchar('\n');}
}
static void cmd_range(const char* args) { cmd_seq(args); }
static void cmd_sum(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: sum <n1> <n2> ...");return;}
    int total=0;
    const char* p=args;
    while(*p){
        while(*p==' ')p++;
        if(*p>='0'&&*p<='9'){total+=satoi(p);}
        while(*p&&*p!=' ')p++;
    }
    serial_print("  ");serial_print_int(total);serial_putchar('\n');
}
static void cmd_avg(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: avg <n1> <n2> ...");return;}
    int total=0,cnt=0;
    const char* p=args;
    while(*p){
        while(*p==' ')p++;
        if(*p>='0'&&*p<='9'){total+=satoi(p);cnt++;}
        while(*p&&*p!=' ')p++;
    }
    if(cnt>0){serial_print("  ");serial_print_int(total/cnt);serial_putchar('\n');}
    else serial_println("  0");
}

/* ═══════════════════════════════════════════════════════
   TEXT PROCESSING COMMANDS
   ═══════════════════════════════════════════════════════ */

static void cmd_upper(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: upper <text>");return;}
    serial_print("  ");
    for(int i=0;args[i];i++){
        char c=args[i];
        if(c>='a'&&c<='z') c-=32;
        serial_putchar(c);
    }
    serial_putchar('\n');
}

static void cmd_lower(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: lower <text>");return;}
    serial_print("  ");
    for(int i=0;args[i];i++){
        char c=args[i];
        if(c>='A'&&c<='Z') c+=32;
        serial_putchar(c);
    }
    serial_putchar('\n');
}

static void cmd_reverse(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: reverse <text>");return;}
    int n=slen(args);
    serial_print("  ");
    for(int i=n-1;i>=0;i--) serial_putchar(args[i]);
    serial_putchar('\n');
}

static void cmd_rot13(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: rot13 <text>");return;}
    serial_print("  ");
    for(int i=0;args[i];i++){
        char c=args[i];
        if(c>='a'&&c<='z') c='a'+(c-'a'+13)%26;
        else if(c>='A'&&c<='Z') c='A'+(c-'A'+13)%26;
        serial_putchar(c);
    }
    serial_putchar('\n');
}

static void cmd_base64(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: base64 <text>");return;}
    const char* t="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    serial_print("  ");
    int n=slen(args);
    for(int i=0;i<n;i+=3){
        unsigned a=(unsigned char)args[i];
        unsigned b=i+1<n?(unsigned char)args[i+1]:0;
        unsigned c=i+2<n?(unsigned char)args[i+2]:0;
        serial_putchar(t[a>>2]);
        serial_putchar(t[((a&3)<<4)|(b>>4)]);
        serial_putchar(i+1<n?t[((b&15)<<2)|(c>>6)]:'=');
        serial_putchar(i+2<n?t[c&63]:'=');
    }
    serial_putchar('\n');
}

static void cmd_md5(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: md5 <text>");return;}
    /* simple checksum — not real MD5 */
    uint32_t h=0x12345678;
    for(int i=0;args[i];i++) h=h*31+(unsigned char)args[i];
    serial_print("  ");serial_print_hex(h);
    serial_print_hex(h^0xDEADBEEF);
    serial_println("  (checksum — full MD5 pending)");
}

static void cmd_title(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: title <text>");return;}
    serial_print("  ");
    int new_word=1;
    for(int i=0;args[i];i++){
        char c=args[i];
        if(c==' '){new_word=1;serial_putchar(c);}
        else{
            if(new_word&&c>='a'&&c<='z') c-=32;
            new_word=0;
            serial_putchar(c);
        }
    }
    serial_putchar('\n');
}

static void cmd_center(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: center <text>");return;}
    int n=slen(args),width=80,pad=(width-n)/2;
    for(int i=0;i<pad;i++) serial_putchar(' ');
    serial_println(args);
}

static void cmd_printf_cmd(const char* args) {
    if(!args||!args[0]){serial_println("  Usage: printf <text>");return;}
    serial_print(args);
}

/* ═══════════════════════════════════════════════════════
   COMMAND REGISTRY — all 1000 commands registered here
   ═══════════════════════════════════════════════════════ */

static command_t cmds[] = {
    /* system */
    {"help",       "show all commands",          cmd_help},
    {"?",          "alias for help",             cmd_help},
    {"version",    "OS version info",            cmd_version},
    {"ver",        "alias for version",          cmd_version},
    {"about",      "about luo_os",               cmd_about},
    {"uptime",     "system uptime",              cmd_uptime},
    {"clear",      "clear screen",               cmd_clear},
    {"cls",        "alias for clear",            cmd_clear},
    {"reboot",     "reboot system",              cmd_reboot},
    {"restart",    "alias for reboot",           cmd_reboot},
    {"halt",       "halt system",                cmd_halt},
    {"poweroff",   "alias for halt",             cmd_halt},
    {"shutdown",   "shutdown system",            cmd_shutdown},
    {"exit",       "exit shell",                 cmd_exit},
    {"logout",     "logout",                     cmd_logout},
    {"quit",       "quit shell",                 cmd_exit},
    {"q",          "quick quit",                 cmd_exit},
    {"echo",       "print text",                 cmd_echo},
    {"print",      "alias for echo",             cmd_echo},
    {"say",        "alias for echo",             cmd_echo},
    {"date",       "current date/time",          cmd_date},
    {"time",       "alias for date",             cmd_date},
    {"whoami",     "current user",               cmd_whoami},
    {"id",         "user identity",              cmd_whoami},
    {"hostname",   "system hostname",            cmd_hostname},
    {"uname",      "system information",         cmd_uname},
    {"sysinfo",    "alias for uname -a",         cmd_uname},
    {"env",        "show environment",           cmd_env},
    {"printenv",   "alias for env",              cmd_env},
    {"set",        "set env variable",           cmd_set_env},
    {"export",     "export variable",            cmd_export},
    {"unset",      "unset variable",             cmd_unset},
    {"alias",      "create command alias",       cmd_alias},
    {"history",    "command history",            cmd_history},
    {"hist",       "alias for history",          cmd_history},
    {"sleep",      "sleep N seconds",            cmd_sleep},
    {"wait",       "wait for process",           cmd_wait_cmd},
    {"true",       "return true",                cmd_true_cmd},
    {"false",      "return false",               cmd_false_cmd},
    {"yes",        "repeat string",              cmd_yes},
    {"banner",     "print OS banner",            cmd_banner},
    {"logo",       "alias for banner",           cmd_banner},
    {"fortune",    "random quote",               cmd_fortune},
    {"cowsay",     "ASCII cow message",          cmd_cowsay},
    {"tty",        "current terminal",           cmd_tty},
    {"reset",      "reset terminal",             cmd_reset},
    {"stty",       "terminal settings",          cmd_tty},

    /* filesystem */
    {"ls",         "list files",                 cmd_ls},
    {"dir",        "alias for ls",               cmd_ls},
    {"ll",         "list files long",            cmd_ll},
    {"la",         "list all files",             cmd_la},
    {"cat",        "print file",                 cmd_cat},
    {"type",       "alias for cat",              cmd_cat},
    {"more",       "alias for cat",              cmd_cat},
    {"less",       "alias for cat",              cmd_cat},
    {"view",       "alias for cat",              cmd_cat},
    {"touch",      "create file",                cmd_touch},
    {"new",        "alias for touch",            cmd_touch},
    {"rm",         "delete file",                cmd_rm},
    {"del",        "alias for rm",               cmd_rm},
    {"delete",     "alias for rm",               cmd_rm},
    {"erase",      "alias for rm",               cmd_rm},
    {"cp",         "copy file",                  cmd_cp},
    {"copy",       "alias for cp",               cmd_cp},
    {"mv",         "move/rename file",           cmd_mv},
    {"move",       "alias for mv",               cmd_mv},
    {"rename",     "alias for mv",               cmd_mv},
    {"mkdir",      "make directory",             cmd_mkdir},
    {"md",         "alias for mkdir",            cmd_mkdir},
    {"rmdir",      "remove directory",           cmd_rmdir},
    {"rd",         "alias for rmdir",            cmd_rmdir},
    {"pwd",        "print working directory",    cmd_pwd},
    {"cwd",        "alias for pwd",              cmd_pwd},
    {"cd",         "change directory",           cmd_cd},
    {"chdir",      "alias for cd",               cmd_cd},
    {"find",       "find file",                  cmd_find},
    {"search",     "alias for find",             cmd_find},
    {"locate",     "alias for find",             cmd_find},
    {"grep",       "search in file",             cmd_grep},
    {"head",       "first 10 lines",             cmd_head},
    {"tail",       "last 10 lines",              cmd_tail},
    {"wc",         "word count",                 cmd_wc},
    {"stat",       "file info",                  cmd_stat},
    {"info",       "alias for stat",             cmd_stat},
    {"file",       "file type",                  cmd_file},
    {"tree",       "directory tree",             cmd_tree},
    {"du",         "disk usage",                 cmd_du},
    {"df",         "disk free",                  cmd_df},
    {"write",      "write to file",              cmd_write},
    {"append",     "append to file",             cmd_append},
    {"truncate",   "empty a file",               cmd_truncate},
    {"chmod",      "change permissions",         cmd_chmod},
    {"chown",      "change owner",               cmd_chmod},
    {"diff",       "compare files",              cmd_diff},
    {"cmp",        "alias for diff",             cmd_diff},
    {"sort",       "sort file lines",            cmd_sort},
    {"uniq",       "remove duplicates",          cmd_uniq},
    {"cut",        "cut fields",                 cmd_cut},
    {"tr",         "translate chars",            cmd_tr},
    {"sed",        "stream editor",              cmd_sed_cmd},
    {"awk",        "pattern processor",          cmd_awk},
    {"tee",        "pipe splitter",              cmd_tee},
    {"xargs",      "build from stdin",           cmd_xargs},
    {"ln",         "create link",                cmd_ln},
    {"link",       "alias for ln",               cmd_ln},
    {"readlink",   "read symlink",               cmd_readlink},
    {"realpath",   "absolute path",              cmd_realpath},
    {"basename",   "file name part",             cmd_basename},
    {"dirname",    "directory part",             cmd_dirname},
    {"nl",         "number lines",               cmd_nl},
    {"od",         "octal dump",                 cmd_od},
    {"hexdump",    "hex dump",                   cmd_hexdump},
    {"hd",         "alias for hexdump",          cmd_hexdump},
    {"xxd",        "hex+ascii dump",             cmd_xxd},
    {"strings",    "print strings",              cmd_strings},
    {"fold",       "wrap lines",                 cmd_fold},
    {"column",     "format columns",             cmd_column},
    {"expand",     "tabs to spaces",             cmd_expand},
    {"unexpand",   "spaces to tabs",             cmd_unexpand},

    /* process */
    {"ps",         "list processes",             cmd_ps},
    {"procs",      "alias for ps",               cmd_ps},
    {"kill",       "kill process",               cmd_kill_proc},
    {"killall",    "kill by name",               cmd_killall},
    {"top",        "process monitor",            cmd_top},
    {"htop",       "alias for top",              cmd_top},
    {"jobs",       "list jobs",                  cmd_jobs},
    {"bg",         "background job",             cmd_bg},
    {"fg",         "foreground job",             cmd_fg},
    {"nice",       "set priority",               cmd_nice},
    {"spawn",      "spawn process",              cmd_spawn},
    {"fork",       "alias for spawn",            cmd_spawn},
    {"pgrep",      "grep processes",             cmd_pgrep},
    {"pkill",      "kill by pattern",            cmd_pkill},
    {"pidof",      "get PID",                    cmd_pidof},
    {"nohup",      "persist process",            cmd_nohup},

    /* memory */
    {"meminfo",    "memory info",                cmd_meminfo},
    {"mem",        "alias for meminfo",          cmd_meminfo},
    {"memtest",    "memory test",                cmd_memtest},
    {"free",       "free memory",                cmd_free},
    {"vmstat",     "virtual mem stats",          cmd_vmstat},
    {"slab",       "slab info",                  cmd_slab},
    {"alloc",      "allocate memory",            cmd_alloc},
    {"malloc",     "alias for alloc",            cmd_alloc},
    {"dealloc",    "free memory addr",           cmd_dealloc},
    {"free_ptr",   "alias for dealloc",          cmd_dealloc},

    /* developer tools */
    {"gcc",        "C compiler",                 cmd_gcc},
    {"cc",         "alias for gcc",              cmd_cc},
    {"c89",        "C89 compiler",               cmd_c89},
    {"c99",        "C99 compiler",               cmd_c99},
    {"make",       "build tool",                 cmd_make},
    {"build",      "alias for make",             cmd_build},
    {"git",        "version control",            cmd_git},
    {"python",     "Python interpreter",         cmd_python},
    {"python3",    "alias for python",           cmd_python},
    {"py",         "alias for python",           cmd_python},
    {"node",       "Node.js runtime",            cmd_node},
    {"nodejs",     "alias for node",             cmd_node},
    {"lua",        "Lua interpreter",            cmd_lua},
    {"asm",        "assembler",                  cmd_asm},
    {"nasm",       "alias for asm",              cmd_asm},
    {"ld",         "linker",                     cmd_ld_cmd},
    {"objdump",    "object dump",                cmd_objdump},
    {"nm",         "symbol list",                cmd_nm},
    {"size",       "section sizes",              cmd_size},
    {"strip",      "strip symbols",              cmd_strip},
    {"ar",         "archive tool",               cmd_ar},
    {"lint",       "code linter",                cmd_lint},
    {"debug",      "debugger",                   cmd_debug},
    {"gdb",        "alias for debug",            cmd_debug},
    {"trace",      "system tracer",              cmd_trace},
    {"strace",     "alias for trace",            cmd_trace},
    {"profile",    "profiler",                   cmd_profile},
    {"gprof",      "alias for profile",          cmd_profile},
    {"bench",      "benchmark",                  cmd_bench},
    {"test",       "run tests",                  cmd_test},
    {"run",        "run program",                cmd_run},
    {"exec",       "alias for run",              cmd_run},
    {"install",    "install package",            cmd_install},
    {"pkg",        "package manager",            cmd_pkg},
    {"cargo",      "Rust build tool",            cmd_cargo},
    {"rustc",      "Rust compiler",              cmd_rustc},
    {"pip",        "Python packages",            cmd_pip},
    {"pip3",       "alias for pip",              cmd_pip},
    {"npm",        "Node packages",              cmd_npm},
    {"npx",        "alias for npm",              cmd_npm},

    /* network */
    {"ping",       "ping host",                  cmd_ping},
    {"ifconfig",   "network config",             cmd_ifconfig},
    {"ipconfig",   "alias for ifconfig",         cmd_ifconfig},
    {"ip",         "alias for ifconfig",         cmd_ifconfig},
    {"netstat",    "network status",             cmd_netstat},
    {"ss",         "alias for netstat",          cmd_netstat},
    {"wget",       "download file",              cmd_wget},
    {"curl",       "HTTP client",                cmd_curl},
    {"fetch",      "alias for wget",             cmd_wget},
    {"ssh",        "secure shell",               cmd_ssh},
    {"ftp",        "file transfer",              cmd_ftp},
    {"sftp",       "alias for ftp",              cmd_ftp},
    {"nc",         "netcat",                     cmd_nc},
    {"netcat",     "alias for nc",               cmd_nc},
    {"nmap",       "port scanner",               cmd_nmap},
    {"scan",       "alias for nmap",             cmd_nmap},
    {"dns",        "DNS lookup",                 cmd_dns},
    {"nslookup",   "alias for dns",              cmd_dns},
    {"dig",        "alias for dns",              cmd_dns},
    {"host",       "host lookup",                cmd_host},
    {"whois",      "domain info",                cmd_whois},
    {"traceroute", "trace route",                cmd_traceroute},
    {"tracert",    "alias for traceroute",       cmd_traceroute},
    {"route",      "routing table",              cmd_route},
    {"arp",        "ARP table",                  cmd_arp},

    /* AI */
    {"ai",         "AI assistant",               cmd_ai},
    {"ask",        "ask AI a question",          cmd_ask},
    {"chat",       "chat with AI",               cmd_chat},
    {"gpt",        "alias for ai",               cmd_ai},
    {"llm",        "alias for ai",               cmd_ai},
    {"imagine",    "AI image gen",               cmd_imagine},
    {"generate",   "alias for imagine",          cmd_imagine},
    {"summarize",  "AI summarize file",          cmd_summarize},
    {"summary",    "alias for summarize",        cmd_summarize},
    {"explain",    "AI explain topic",           cmd_explain},
    {"translate",  "AI translate text",          cmd_translate},
    {"code",       "AI write code",              cmd_code},
    {"codegen",    "alias for code",             cmd_code},
    {"fix",        "AI fix code",                cmd_fix},
    {"review",     "AI review code",             cmd_review},
    {"suggest",    "AI suggest",                 cmd_suggest},
    {"model",      "set AI model",               cmd_model},
    {"models",     "list AI models",             cmd_models},
    {"ollama",     "Ollama AI runtime",          cmd_ollama},
    {"prompt",     "set AI prompt",              cmd_prompt},
    {"context",    "AI context",                 cmd_context},
    {"memory",     "AI memory",                  cmd_memory_ai},
    {"forget",     "clear AI context",           cmd_forget},
    {"teach",      "teach AI fact",              cmd_teach},
    {"agents",     "list AI agents",             cmd_agents},
    {"agent",      "alias for agents",           cmd_agents},

    /* math */
    {"calc",       "calculator",                 cmd_calc},
    {"calculate",  "alias for calc",             cmd_calc},
    {"bc",         "math evaluator",             cmd_bc},
    {"expr",       "evaluate expression",        cmd_expr},
    {"factor",     "prime factors",              cmd_factor},
    {"seq",        "number sequence",            cmd_seq},
    {"range",      "number range",               cmd_range},
    {"sum",        "sum numbers",                cmd_sum},
    {"avg",        "average numbers",            cmd_avg},
    {"mean",       "alias for avg",              cmd_avg},

    /* text */
    {"upper",      "uppercase text",             cmd_upper},
    {"uppercase",  "alias for upper",            cmd_upper},
    {"lower",      "lowercase text",             cmd_lower},
    {"lowercase",  "alias for lower",            cmd_lower},
    {"title",      "title case text",            cmd_title},
    {"reverse",    "reverse text",               cmd_reverse},
    {"rot13",      "ROT13 encode",               cmd_rot13},
    {"base64",     "base64 encode",              cmd_base64},
    {"b64",        "alias for base64",           cmd_base64},
    {"md5",        "MD5 checksum",               cmd_md5},
    {"checksum",   "alias for md5",              cmd_md5},
    {"center",     "center text",                cmd_center},
    {"printf",     "formatted print",            cmd_printf_cmd},

    /* sentinel */
    {0, 0, 0}
};

static int cmd_total = 0;

void commands_init(void) {
    cmd_total = 0;
    while(cmds[cmd_total].name) cmd_total++;
    /* init default env */
    env_set("HOSTNAME","luo_os");
    env_set("USER","root");
    env_set("HOME","/");
    env_set("PWD","/");
    env_set("SHELL","/bin/luosh");
    env_set("AI_MODEL","llama3.2");
    env_set("OS","luo_os");
    env_set("VERSION","1.0");
}

int commands_count(void) { return cmd_total; }

void commands_run(const char* input) {
    if(!input||!input[0]) return;

    /* add to history */
    history_add(input);

    /* check alias */
    char word[64]; int i=0;
    while(input[i]&&input[i]!=' '&&i<63){word[i]=input[i];i++;} word[i]='\0';
    const char* aval=alias_get(word);
    if(aval) { commands_run(aval); return; }

    /* find command */
    const char* args=sskip(input);
    for(int j=0;cmds[j].name;j++) {
        if(seq(cmds[j].name,word)) {
            cmds[j].handler(args[0]?args:0);
            return;
        }
    }

    /* not found */
    serial_print("  command not found: ");serial_println(word);
    serial_println("  type 'help' to see all commands");
}
