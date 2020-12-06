
#ifndef _TVLB_H
#define _TVLB_H 1

#ifndef __USE_GNU
#define __USE_GNU 
#endif

static int am_pinned = -1;

#include <sys/ioctl.h>
#include <string.h>

#include <sys/time.h>
#include <sys/resource.h>

#if __linux__
#if PERF
#include <linux/perf_event.h>
#include <linux/hw_breakpoint.h>
#include <jevents.h>
#endif
#endif

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/ioctl.h>

#include <stdlib.h>
#include <stdlib.h>

#include <pthread.h>
#include <sched.h>
#include <inttypes.h>

#ifndef _GOT_PROFILE_H
#if defined(__x86_64__)
static inline void data_barrier(void)
{
        asm volatile("mfence\n" ::: "memory");
}
#elif defined(__aarch64__)
static inline void data_barrier(void)
{
        asm volatile("dsb sy\n" ::: "memory");
}
#else
#error unsupported architecture.
#endif
#endif

#define PAGE 4096
#define LEAFSHAREFILE  ".tvlbsinglepagefile"
#define LEAFSYNCFILE   ".tvlbsyncfile"
#define SECRETBITS 256

#ifndef TVLB_PROF
#define CRYPTLOOP                                                                   \
    static int have_executed = 0;                                                   \
    if(!gcry_mysharestruct) { gcry_mysharestruct = get_sharestruct(); }             \
    assert(gcry_mysharestruct->magic == MAGIC);                                     \
    if(ben) have_executed++;                                                              \
    if(have_executed >= 2) { ben = 0; }                  \
    int groundtruth_bits[30000];                                                    \
    int n_groundtruth_bits = 0;                                                     \
    if(ben) {                                                                           \
     gcry_mysharestruct->bit_position = 0;                                              \
           gcry_mysharestruct->target_started = __LINE__;                           \
     }

#define CRYPTLOOP_START(idx) int idxval=(1+(idx%100))*256;

#define CRYPTLOOP_VALUE(v) if(gcry_mysharestruct->groundtruth_bits && ben) { gcry_mysharestruct->bit_position = idxval + v;  data_barrier(); \
    groundtruth_bits[n_groundtruth_bits++] = v; \
}

#define CRYPTLOOP_END                                \
    if(ben && gcry_mysharestruct->groundtruth_bits) {       \
        gcry_mysharestruct->bit_position = 0;        \
    }                                                \
    if(have_executed >= 2) { fprintf(stderr, "# no more\n"); gcry_mysharestruct->target_started = 0;        exit(0); }                  \
    if(ben && gcry_mysharestruct->auto_end) { \
      gcry_mysharestruct->target_started = 0;        \
    } \
    int _j, _i; \
          if(ben) { printf("# target: "); \
          for (_i=0; _i < n_groundtruth_bits; _i++) { \
              printf("%d", groundtruth_bits[_i]); \
          } \
    printf("\n"); }
#else
#define CRYPTLOOP
#define CRYPTLOOP_START(idx) {}
#define CRYPTLOOP_VALUE(v) {}
#define CRYPTLOOP_END
#endif /* TVLB_PROF */

#define MAGIC 0x31337

#if IACA                                                                                                                                                                                                                                                                                                                                                                                         
#define IACASTART         "\n\t  movl $111, %%ebx"   "\n\t  .byte 0x64, 0x67, 0x90 \n"    
#define IACAEND           "\n\t  movl $222, %%ebx"   "\n\t  .byte 0x64, 0x67, 0x90 \n"    
#else
#define IACASTART  
#define IACAEND    
#endif

#define SHAREFILE ".singlepagefile"

/* Scratch register to use */
#if defined(__x86_64__)
#define SCRATCHREG  "rdx"
#define SCRATCHREG1 "rdx"
#define SCRATCHREG2 "rcx"
#define SCRATCHREGS SCRATCHREG1, SCRATCHREG2
#elif defined(__aarch64__)
#define SCRATCHREG1 "x20"
#define SCRATCHREG2 "x21"
#define SCRATCHREG3 "x22"
#define SCRATCHREG4 "x23"
#define SCRATCHREG5 "x24"
#define SCRATCHREGS SCRATCHREG1, SCRATCHREG2, SCRATCHREG3, SCRATCHREG4, SCRATCHREG5
#endif

struct sharestruct {
    volatile int target_started;
    volatile int bit_position;
    volatile int desired_bit_position;
    volatile int sample;
    volatile int groundtruth_bits;   /* only set bit_position if groundtruth is set */
    volatile int magic;
    volatile int covert_bit;
    volatile int covert_bit_pos;
    volatile int securemode;
    volatile int auto_end; /* target_started = 0 automatically */
};

#ifndef NO_GSS

static int set_fileno = -1;

static void tvlb_fileno(int f)
{
    set_fileno = f;
    assert(set_fileno >= 0);
    assert(set_fileno < 32); /* page limit */
}


static int createfile(const char *leaffn)
{

    assert(!strchr(leaffn, '/'));

    const char *homedir = getenv("HOME");
    if(!homedir) homedir = "/tmp";
    char fullfn[2000];
    if(set_fileno < 0) {
        char *fn_env = getenv("SHAREFILENO");
        if(!fn_env) { exit(1); }
	tvlb_fileno(atoi(fn_env));
    }
    assert(set_fileno >= 0);
    sprintf(fullfn, "%s/%s-file%d", homedir, leaffn, set_fileno);


        int fd;
        struct stat sb;
        if(stat(fullfn, &sb) != 0 || sb.st_size != PAGE) {
            char sharebuf[PAGE];
            memset(sharebuf, 0, sizeof(sharebuf));
                fd = open(fullfn, O_RDWR | O_CREAT | O_TRUNC, 0644);
                if(fd < 0) {
			perror("open");
                        fprintf(stderr, "createfile: line %d: couldn't create shared file %s. homedir: %s leaffn: %s\n", __LINE__, fullfn, homedir, leaffn);
                        exit(1);
                }
                if(write(fd, sharebuf, PAGE) != PAGE) {
                        fprintf(stderr, "createfile: couldn't write shared file\n");
                        exit(1);
                }
                return fd;
        }

        assert(sb.st_size == PAGE);

        fd = open(fullfn, O_RDWR, 0644);
        if(fd < 0) {
            perror(fullfn);
                fprintf(stderr, "createfile: couldn't open shared file\n");
                exit(1);
        }
        return fd;

}

static volatile struct sharestruct *get_sharestruct()
{
#ifndef TVLB_PROF
    int fd_uio = open("/dev/uio0", O_RDWR);
    if(fd_uio >= 0) {
    	volatile struct sharestruct *uio_ret = (volatile struct sharestruct *) mmap(NULL, PAGE*1000, PROT_READ|PROT_WRITE, MAP_SHARED, fd_uio, 1*PAGE);
        if(uio_ret == MAP_FAILED) {
            perror("mmap");
		    exit(1);
	    }
        char *fn_env = getenv("SHAREFILENO");
	if(!fn_env) { fprintf(stderr, "no SHAREFILENO\n"); exit(1); }
	tvlb_fileno(atoi(fn_env));
#define OFFSET 128
	assert(OFFSET > sizeof(struct sharestruct));
        return (volatile struct sharestruct *) ((char *) uio_ret+(OFFSET*set_fileno));
    }

    int fd = createfile(LEAFSYNCFILE);

	volatile struct sharestruct *ret = (volatile struct sharestruct *) mmap(NULL, PAGE, PROT_READ|PROT_WRITE, MAP_SHARED|MAP_FILE, fd, 0);
	if(ret == MAP_FAILED) {
		perror("mmap");
		exit(1);
	}

	return ret;
#else
    static struct sharestruct dummy;
    return &dummy;
#endif /* TVLB_PROF */
}
#endif

#ifndef TVLB_PROF
static void _pin_cpu(size_t i)
{
        cpu_set_t cpu_set;
        pthread_t thread;

        thread = pthread_self();

        fprintf(stderr, "# pin_cpu %ld, CPU_SETSIZE %d\n", i, CPU_SETSIZE);
        assert (i >= 0);
        assert (i < CPU_SETSIZE);

        CPU_ZERO(&cpu_set);
        CPU_SET(i, &cpu_set);

        int v = pthread_setaffinity_np(thread, sizeof cpu_set, &cpu_set);
        if(v != 0) { perror("pthread_setaffinity_np"); exit(1); }
#ifndef QUIET
        fprintf(stdout, "# tvlb cpu %d\n", (int) i);
#endif
        am_pinned=i;

        int rv = setpriority(PRIO_PROCESS, 0, -20);
        if(rv < 0) { perror("setpriority"); exit(1); }
}

static void pin_cpu(size_t i) { _pin_cpu(i); }

#ifndef NO_GSS
static void absynthe_init(void)
{
    char *pincpu_str = getenv("PINCPU");
    assert(pincpu_str);
    int pincpu_i = atoi(pincpu_str);
    fprintf(stderr, "# PINCPU %s, %d, CPU_SETSIZE %d\n", pincpu_str, pincpu_i, CPU_SETSIZE);
    _pin_cpu(pincpu_i);
    char *sharestr = getenv("SHAREFILENO");
    assert(sharestr);
    tvlb_fileno(atoi(sharestr));
}
#endif


#else
#define pin_cpu(X) {}
#endif /* TVLB_PROF */

#if PERF
// #define EVENT "STLB_LOAD_MISSES.MISS_CAUSES_A_WALK"
//#define EVENT "DTLB_LOAD_MISSES.MISS_CAUSES_A_WALK"
//#define EVENT2 "dtlb_store_misses.walk_pending"
#if defined(__aarch64__)
#define EVENT_CF "r23" // 0x0023 STALL_FRONTEND Cycle on which no operation issued because there are no operations to issue.
#define EVENT_C0 "r24" // 0x0024 STALL_BACKEND  Cycle on which no operation issued due to back-end resources being unavailable.
// LB, ST are from https://www.marvell.com/documents/hrur6mybdvk5uki1w0z7/
#define EVENT_LBSTALLS "r158" // 0x0158 M LRQ_RECYCLE Number of cycles in which one or more valid micro-ops did not dis-patch due to LRQ full
#define EVENT_SBSTALLS "r159" // 0x0159 M SRQ_RECYCLE Number of cycles in which one or more valid micro-ops did not dis-patch due to SRQ full.
#define EVENT_GPRSTALLS "r155"// 0x0155 M GPR_RECYCLE Number of cycles in which one or more valid micro-ops did not dis-patch because GPR renamer pool is empty.
#define EVENT_INST_RETIRED "r8" // 0x0008 A INST_RETIRED Instruction architecturally executed
#else
#define EVENT_C0 "uops_executed.core_cycles_none"
#define EVENT_CANY "uops_executed.core_cycles_ge_1"
#define EVENT_SBSTALLS "resource_stalls.sb"
#define EVENT_RSSTALLS "resource_stalls.rs"
#endif

#define MAX_EVENTS 10
#define MAX_RECORDINGS 500000
struct pe {
        char *name;
        int idx;
        int fd;
        struct perf_event_attr attr;
        struct { uint64_t value, index; } recordings[MAX_RECORDINGS];
} _all_perf_events[MAX_EVENTS];
int _perf_events = 0;

#define PERF_INIT(eventname, event_index)  { \
        event_index = _perf_events++; \
        assert(event_index >= 0); \
        assert(event_index < MAX_EVENTS); \
        struct pe *tpe = &_all_perf_events[event_index]; \
        tpe->name = eventname; \
        tpe->idx = 0; \
        memset(&tpe->recordings, 0, sizeof(tpe->recordings)); \
        { \
        if (resolve_event(eventname, &tpe->attr) < 0) {		\
                perror("resolve_event " eventname);		\
                exit(1);		\
        }		\
		\
        if((tpe->fd = perf_event_open(&tpe->attr, 0, -1, -1, PERF_FLAG_FD_NO_GROUP)) < 0) {		\
                perror("perf_event_open " eventname);		\
                exit(1);		\
        }  \
        ioctl(tpe->fd, PERF_EVENT_IOC_RESET, 0); \
        ioctl(tpe->fd, PERF_EVENT_IOC_ENABLE, 0); \
        }  }

#define PERF_READ(ev, ixvar)    do { \
    int _r; \
    assert(ev >= 0); \
    assert(ev < MAX_EVENTS); \
    struct pe *tpe = &_all_perf_events[ev]; \
    int idx = tpe->idx++; \
    assert(idx >= 0); \
    assert(idx < MAX_RECORDINGS); \
    tpe->recordings[idx].index = ixvar; \
    _r = read(tpe->fd, &tpe->recordings[idx].value, sizeof(uint64_t)); \
    assert(_r == sizeof(uint64_t)); \
} while(0)

#define DUMP_PERF { \
    int ev; \
    for(ev = 0; ev < _perf_events; ev++) { \
        int idx;            \
        printf("PERF %s ", _all_perf_events[ev].name);      \
        for(idx = 0; idx < _all_perf_events[ev].idx; idx++) {   \
                printf("%lu %lu ", _all_perf_events[ev].recordings[idx].value, _all_perf_events[ev].recordings[idx].index); \
        }   \
        printf("\n"); \
    }\
}

#endif

#ifdef TVLB_PROF

#include <sanitizer/dfsan_interface.h>

#define TAINTINFO_CMP_DUMP_ONCE 0

dfsan_label taintinfo_l __attribute__((weak));
int taintinfo_init_done __attribute__((weak));
static inline dfsan_label taintinfo_get_label()
{
	if (taintinfo_init_done)
		return taintinfo_l;
	taintinfo_init_done = 1;
	taintinfo_l = dfsan_create_label("", NULL);
	return taintinfo_l;
}

__attribute__((used)) int taintinfo_dump_cmp_skip;
__attribute__((noinline)) __attribute__((weak)) __attribute__((used)) void taintinfo_dump_cmp_dbg_hook(int cmp)
{
  (void)(cmp);
  asm ("");
}

static inline void taintinfo_dump_cmp(int cmp, int *dumped_t, int *dumped_nt, const char *file, int line, const char *func)
{
	taintinfo_dump_cmp_dbg_hook(cmp);
	if (!taintinfo_dump_cmp_skip) {
		if (TAINTINFO_CMP_DUMP_ONCE && *dumped_t && *dumped_nt)
			return;
		dfsan_label l = dfsan_get_label(cmp);
		int tainted = dfsan_has_label(l, taintinfo_get_label());
		if (TAINTINFO_CMP_DUMP_ONCE && ((tainted && (*dumped_t)) || (!tainted && (*dumped_nt))))
			return;
		fprintf(stderr, "[%s:%d:%s] dump_cmp(): cmp=%d, tainted=%d\n", file, line, func, cmp, tainted);
		if (tainted)
			*dumped_t=1;
		else
			*dumped_nt=1;
	}
}

static inline void taintinfo_dump(const void *ptr, size_t size, const char *file, int line, const char *func)
{
	dfsan_label l = dfsan_read_label(ptr, size);
	int tainted = dfsan_has_label(l, taintinfo_get_label());
	fprintf(stderr, "[%s:%d:%s] dump(): ptr=%p, size=%zu, tainted=%d\n", file, line, func, ptr, size, tainted);
}

static inline void taintinfo_taint(const void *ptr, size_t size, const char *file, int line, const char *func)
{
	fprintf(stderr, "[%s:%d:%s] taint(): ptr=%p, size=%zu\n", file, line, func, ptr, size);
	dfsan_set_label(taintinfo_get_label(), (void*)ptr, size);
}

static inline void taintinfo_prop(const void *src, size_t src_size, const void *dst, size_t dst_size,
	const char *file, int line, const char *func)
{
	dfsan_label src_l = dfsan_read_label(src, src_size);
	dfsan_label dst_l = dfsan_read_label(dst, dst_size);
	fprintf(stderr, "[%s:%d:%s] prop(): src=%p, src_size=%zu, dst=%p, dst_size=%zu, prop=%d\n", file, line, func,
		src, src_size, dst, dst_size, !dfsan_has_label(dst_l, src_l));
	dfsan_set_label(src_l, (void*)dst, dst_size);
}

#define TAINTINFO_TAINT(X, S) { taintinfo_taint(X, S, __FILE__, __LINE__, __FUNCTION__); }
#define TAINTINFO_PROP(X, S, XP, SP) { taintinfo_prop(X, S, XP, SP, __FILE__, __LINE__, __FUNCTION__); }
#define TAINTINFO_DUMP(X, S) { taintinfo_dump(X, S, __FILE__, __LINE__, __FUNCTION__); }
#define TAINTINFO_CMP(X, F, L, P) ({static int _TIX=0; static int _TIY=0; _Bool cmp = X; taintinfo_dump_cmp((int)cmp, &_TIX, &_TIY, F, L, P); cmp;})
#define TAINTINFO_IF(X) if (TAINTINFO_CMP(X, __FILE__, __LINE__, __FUNCTION__))

#else

#define TAINTINFO_TAINT(X,S) {}
#define TAINTINFO_IF(X) if (X)

#endif /* TVLB_PROF */

#endif
