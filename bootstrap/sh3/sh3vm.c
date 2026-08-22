/*
 * Saga SH-3 bootstrap VM.
 *
 * This machine is intentionally language-neutral. It understands only a small
 * dynamically-tagged stack instruction set, generic text/list values, function
 * calls, and explicit host file/argv primitives. It contains no Saga lexer,
 * parser, type rules, class/generic semantics, option/result semantics, or
 * Standard Core library policy. Those live in canonical .saga sources.
 */
#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum { V_UNIT=0, V_INT=1, V_BOOL=2, V_TEXT=3, V_LIST=4 } VKind;
typedef struct Value Value;
typedef struct List { size_t n, cap, refs; Value *v; } List;
struct Value { VKind k; int64_t i; char *s; List *l; };

typedef struct Instr { char *op; char *a; char *b; int line; } Instr;
typedef struct Label { char *name; size_t pc; } Label;
typedef struct Func {
    char *name; int argc, locals;
    Instr *code; size_t ncode, capcode;
    Label *labels; size_t nlabels, caplabels;
} Func;
typedef struct Program { Func *f; size_t n, cap; char *entry; int nglobals; Value *globals; } Program;

typedef struct Stack { Value *v; size_t n, cap; } Stack;

static void die(const char *m) { fprintf(stderr,"sh3vm: %s\n",m); exit(70); }
static void *xmalloc(size_t n){ void *p=malloc(n?n:1); if(!p) die("out of memory"); return p; }
static void *xrealloc(void *p,size_t n){ void*q=realloc(p,n?n:1); if(!q) die("out of memory"); return q; }
static char *xstrdup(const char*s){ size_t n=strlen(s); char*p=xmalloc(n+1); memcpy(p,s,n+1); return p; }
static Value vu(void){ Value v={V_UNIT,0,NULL,NULL}; return v; }
static Value vi(int64_t x){ Value v={V_INT,x,NULL,NULL}; return v; }
static Value vb(int x){ Value v={V_BOOL,x?1:0,NULL,NULL}; return v; }
static Value vt(const char*s){ Value v={V_TEXT,0,xstrdup(s?s:""),NULL}; return v; }
static Value vl(void){ Value v={V_LIST,0,NULL,xmalloc(sizeof(List))}; v.l->n=0;v.l->cap=0;v.l->refs=1;v.l->v=NULL;return v; }
static void list_add(List*l,Value v);
static Value clone(Value x){
    if(x.k==V_TEXT) return vt(x.s);
    if(x.k==V_LIST && x.l){ x.l->refs++; return x; }
    return x;
}
static void drop(Value v){
    if(v.k==V_TEXT) free(v.s);
    else if(v.k==V_LIST&&v.l){
        if(v.l->refs==0) die("list refcount underflow");
        v.l->refs--;
        if(v.l->refs==0){ for(size_t i=0;i<v.l->n;i++)drop(v.l->v[i]); free(v.l->v);free(v.l); }
    }
}
static Value list_copy(Value src){
    if(src.k!=V_LIST||!src.l) die("list_copy type");
    Value r=vl();
    for(size_t i=0;i<src.l->n;i++) list_add(r.l,clone(src.l->v[i]));
    return r;
}
static void push(Stack*s,Value v){ if(s->n==s->cap){s->cap=s->cap?2*s->cap:32;s->v=xrealloc(s->v,s->cap*sizeof(Value));} s->v[s->n++]=v; }
static Value pop(Stack*s){ if(!s->n) die("stack underflow"); return s->v[--s->n]; }
static Value peek(Stack*s){ if(!s->n) die("stack underflow"); return s->v[s->n-1]; }
static int truth(Value v){ if(v.k==V_BOOL||v.k==V_INT) return v.i!=0; if(v.k==V_TEXT)return v.s&&*v.s; if(v.k==V_LIST)return v.l&&v.l->n; return 0; }
static void list_add(List*l,Value v){ if(l->n==l->cap){l->cap=l->cap?2*l->cap:4;l->v=xrealloc(l->v,l->cap*sizeof(Value));} l->v[l->n++]=v; }

static int hexval(char c){ if(c>='0'&&c<='9')return c-'0'; if(c>='a'&&c<='f')return 10+c-'a'; if(c>='A'&&c<='F')return 10+c-'A'; return -1; }
static char *unhex(const char*h){ if(!h) die("missing hex text"); if(!strcmp(h,"-")) return xstrdup(""); size_t n=strlen(h); if(n%2)die("invalid hex text"); for(size_t i=0;i<n;i+=2){if(hexval(h[i])<0||hexval(h[i+1])<0)die("invalid hex text");} char*s=xmalloc(n/2+1); for(size_t i=0;i<n;i+=2){int a=hexval(h[i]),b=hexval(h[i+1]);s[i/2]=(char)((a<<4)|b);} s[n/2]=0; return s; }

static void add_instr(Func*f,const char*op,const char*a,const char*b,int line){ if(f->ncode==f->capcode){f->capcode=f->capcode?2*f->capcode:64;f->code=xrealloc(f->code,f->capcode*sizeof(Instr));} f->code[f->ncode++]=(Instr){xstrdup(op),a?xstrdup(a):NULL,b?xstrdup(b):NULL,line}; }
static void add_label(Func*f,const char*n,size_t pc){ if(f->nlabels==f->caplabels){f->caplabels=f->caplabels?2*f->caplabels:16;f->labels=xrealloc(f->labels,f->caplabels*sizeof(Label));} f->labels[f->nlabels++]=(Label){xstrdup(n),pc}; }
static size_t label_pc(Func*f,const char*n){ for(size_t i=0;i<f->nlabels;i++)if(!strcmp(f->labels[i].name,n))return f->labels[i].pc; fprintf(stderr,"unknown label %s in %s\n",n,f->name);exit(70); }
static Func *find_func(Program*p,const char*n){for(size_t i=0;i<p->n;i++)if(!strcmp(p->f[i].name,n))return&p->f[i];return NULL;}
static Func *add_func(Program*p,const char*n,int argc,int locals){if(p->n==p->cap){p->cap=p->cap?2*p->cap:16;p->f=xrealloc(p->f,p->cap*sizeof(Func));}Func*f=&p->f[p->n++];memset(f,0,sizeof(*f));f->name=xstrdup(n);f->argc=argc;f->locals=locals;return f;}
static void free_program(Program *p){
    if(!p)return;
    for(size_t i=0;i<p->n;i++){
        Func*f=&p->f[i];
        free(f->name);
        for(size_t j=0;j<f->ncode;j++){free(f->code[j].op);free(f->code[j].a);free(f->code[j].b);}
        for(size_t j=0;j<f->nlabels;j++)free(f->labels[j].name);
        free(f->code);free(f->labels);
    }
    for(int i=0;i<p->nglobals;i++)drop(p->globals[i]);
    free(p->globals);free(p->f);free(p->entry);
    memset(p,0,sizeof(*p));
}

static Program load_program(const char*path){
    FILE*fp=fopen(path,"rb"); if(!fp){perror(path);exit(66);} Program p={0}; Func*cur=NULL; char line[65536]; int ln=0;
    while(fgets(line,sizeof(line),fp)){ ln++; size_t n=strlen(line);while(n&& (line[n-1]=='\n'||line[n-1]=='\r'))line[--n]=0; char*q=line;while(*q&&isspace((unsigned char)*q))q++; if(!*q||*q=='#')continue;
        char*op=strtok(q," \t");char*a=strtok(NULL," \t");char*b=strtok(NULL," \t");char*c=strtok(NULL," \t");
        if(!strcmp(op,"SH3BC1"))continue;
        if(!strcmp(op,"GLOBALS")){ if(!a)die("GLOBALS missing count"); p.nglobals=atoi(a); p.globals=xmalloc((size_t)p.nglobals*sizeof(Value)); for(int gi=0;gi<p.nglobals;gi++)p.globals[gi]=vu(); continue; }
        if(!strcmp(op,"ENTRY")){ if(!a)die("ENTRY missing name"); free(p.entry); p.entry=unhex(a); continue; }
        if(!strcmp(op,"FUNC")){ if(!a||!b||!c)die("FUNC syntax"); char*name=unhex(a);cur=add_func(&p,name,atoi(b),atoi(c));free(name);continue; }
        if(!strcmp(op,"END")){cur=NULL;continue;}
        if(!cur)die("instruction outside FUNC");
        if(!strcmp(op,"LABEL")){ if(!a)die("LABEL missing");add_label(cur,a,cur->ncode);continue; }
        add_instr(cur,op,a,b,ln);
    }
    fclose(fp); if(!p.entry)die("missing ENTRY"); return p;
}

static char *value_text(Value v){ char buf[128]; if(v.k==V_TEXT)return xstrdup(v.s); if(v.k==V_INT){snprintf(buf,sizeof(buf),"%" PRId64,v.i);return xstrdup(buf);} if(v.k==V_BOOL)return xstrdup(v.i?"true":"false"); if(v.k==V_UNIT)return xstrdup("unit"); if(v.k==V_LIST){size_t cap=32,n=0;char*r=xmalloc(cap);r[n++]='[';r[n]=0;for(size_t i=0;i<v.l->n;i++){char*t=value_text(v.l->v[i]);size_t z=strlen(t);while(n+z+4>cap){cap*=2;r=xrealloc(r,cap);}if(i){r[n++]=',';r[n++]=' ';}memcpy(r+n,t,z);n+=z;r[n]=0;free(t);}while(n+2>cap){cap*=2;r=xrealloc(r,cap);}r[n++]=']';r[n]=0;return r;}return xstrdup("?"); }
static Value builtin(const char*name,Value*args,int n,int host_argc,char**host_argv){
    if(!strcmp(name,"len")){ if(n!=1)die("len arity"); if(args[0].k==V_TEXT)return vi((int64_t)strlen(args[0].s)); if(args[0].k==V_LIST)return vi((int64_t)args[0].l->n); die("len type"); }
    if(!strcmp(name,"append")){ if(n!=2||args[0].k!=V_LIST)die("append type"); Value r=list_copy(args[0]);list_add(r.l,clone(args[1]));return r; }
    if(!strcmp(name,"set_at")){ if(n!=3||args[0].k!=V_LIST||args[1].k!=V_INT)die("set_at type"); Value r=list_copy(args[0]); if(args[1].i<0||(uint64_t)args[1].i>=r.l->n)die("set_at range"); drop(r.l->v[args[1].i]); r.l->v[args[1].i]=clone(args[2]); return r; }
    if(!strcmp(name,"push")){ if(n!=2||args[0].k!=V_LIST)die("push type"); list_add(args[0].l,clone(args[1]));return clone(args[0]); }
    if(!strcmp(name,"substring")){ if(n!=3||args[0].k!=V_TEXT)die("substring type");int64_t a=args[1].i,b=args[2].i;size_t L=strlen(args[0].s);if(a<0)a=0;if(b<a)b=a;if((uint64_t)a>L)a=(int64_t)L;if((uint64_t)b>L)b=(int64_t)L;char*r=xmalloc((size_t)(b-a)+1);memcpy(r,args[0].s+a,(size_t)(b-a));r[b-a]=0;Value v=vt(r);free(r);return v; }
    if(!strcmp(name,"slice")){ if(n!=3||args[0].k!=V_LIST||args[1].k!=V_INT||args[2].k!=V_INT)die("slice type"); int64_t a=args[1].i,b=args[2].i; if(a<0)a=0;if(b<a)b=a;if((uint64_t)a>args[0].l->n)a=(int64_t)args[0].l->n;if((uint64_t)b>args[0].l->n)b=(int64_t)args[0].l->n; Value r=vl(); for(int64_t j=a;j<b;j++)list_add(r.l,clone(args[0].l->v[j])); return r; }
    if(!strcmp(name,"find_text")){ if(n!=2||args[0].k!=V_TEXT||args[1].k!=V_TEXT)die("find_text type");char*p=strstr(args[0].s,args[1].s);return vi(p?(int64_t)(p-args[0].s):-1); }
    if(!strcmp(name,"replace")){ if(n!=3||args[0].k!=V_TEXT||args[1].k!=V_TEXT||args[2].k!=V_TEXT)die("replace type"); const char*src=args[0].s; const char*old=args[1].s; const char*nw=args[2].s; size_t ol=strlen(old), nl=strlen(nw); if(ol==0)return vt(src); size_t count=0; const char*q=src; while((q=strstr(q,old))){count++;q+=ol;} size_t outn=strlen(src)+count*(nl-ol); char*out=xmalloc(outn+1); char*w=out; q=src; const char*m; while((m=strstr(q,old))){size_t z=(size_t)(m-q);memcpy(w,q,z);w+=z;memcpy(w,nw,nl);w+=nl;q=m+ol;} strcpy(w,q); Value v=vt(out);free(out);return v; }
    if(!strcmp(name,"byteord")){ if(n!=1||args[0].k!=V_TEXT||strlen(args[0].s)<1)die("byteord type");return vi((unsigned char)args[0].s[0]); }
    if(!strcmp(name,"bytechr")){ if(n!=1||args[0].k!=V_INT||args[0].i<0||args[0].i>255)die("bytechr type");char z[2]={(char)(unsigned char)args[0].i,0};return vt(z); }
    if(!strcmp(name,"starts_with")){ if(n!=2||args[0].k!=V_TEXT||args[1].k!=V_TEXT)die("starts_with type");size_t z=strlen(args[1].s);return vb(!strncmp(args[0].s,args[1].s,z)); }
    if(!strcmp(name,"ends_with")){ if(n!=2||args[0].k!=V_TEXT||args[1].k!=V_TEXT)die("ends_with type");size_t a=strlen(args[0].s),b=strlen(args[1].s);return vb(a>=b&&!memcmp(args[0].s+a-b,args[1].s,b)); }
    if(!strcmp(name,"text")){ if(n!=1)die("text arity");char*s=value_text(args[0]);Value v=vt(s);free(s);return v; }
    if(!strcmp(name,"int")){ if(n!=1)die("int arity");if(args[0].k==V_INT)return args[0];if(args[0].k==V_BOOL)return vi(args[0].i);if(args[0].k==V_TEXT){char*e=NULL;errno=0;long long x=strtoll(args[0].s,&e,10);if(errno||!e||*e)die("int parse");return vi((int64_t)x);}die("int type"); }
    if(!strcmp(name,"ord")){ if(n!=1||args[0].k!=V_TEXT||strlen(args[0].s)!=1)die("ord type");return vi((unsigned char)args[0].s[0]); }
    if(!strcmp(name,"chr")){ if(n!=1||args[0].k!=V_INT||args[0].i<0||args[0].i>127)die("chr type");char s[2]={(char)args[0].i,0};return vt(s); }
    if(!strcmp(name,"read_text")){ if(n!=1||args[0].k!=V_TEXT)die("read_text type");FILE*f=fopen(args[0].s,"rb");if(!f){perror(args[0].s);exit(66);}fseek(f,0,SEEK_END);long z=ftell(f);fseek(f,0,SEEK_SET);char*s=xmalloc((size_t)z+1);if(z&&fread(s,1,(size_t)z,f)!=(size_t)z)die("read failed");s[z]=0;fclose(f);Value v=vt(s);free(s);return v; }
    if(!strcmp(name,"write_text")){ if(n!=2||args[0].k!=V_TEXT||args[1].k!=V_TEXT)die("write_text type");FILE*f=fopen(args[0].s,"wb");if(!f){perror(args[0].s);exit(66);}fwrite(args[1].s,1,strlen(args[1].s),f);fclose(f);return vu(); }
    if(!strcmp(name,"args")){ Value r=vl();for(int i=0;i<host_argc;i++)list_add(r.l,vt(host_argv[i]));return r; }
    if(!strcmp(name,"host_available")){ if(n!=1||args[0].k!=V_TEXT)die("host_available type"); return vb(0); }
    if(!strcmp(name,"host_call")){ if(n!=2||args[0].k!=V_TEXT||args[1].k!=V_LIST)die("host_call type"); die("host capability unavailable"); }
    if(!strcmp(name,"exit")){ if(n!=1||args[0].k!=V_INT)die("exit type");exit((int)args[0].i); }
    fprintf(stderr,"sh3vm: unknown builtin %s\n",name);exit(70);
}

static Value exec_func(Program*p,Func*f,Value*argv,int argc,int host_argc,char**host_argv,int depth){
    if (depth > 4096) die("call depth exceeded");
    if (argc != f->argc) { fprintf(stderr,"arity mismatch %s\n",f->name); exit(70); }
    int nloc=f->locals;
    if(nloc<f->argc)nloc=f->argc;
    Value*loc=xmalloc((size_t)nloc*sizeof(Value));
    for(int i=0;i<nloc;i++)loc[i]=vu();
    for(int i=0;i<argc;i++)loc[i]=clone(argv[i]);
    Stack st={0}; size_t pc=0; Value ret=vu(); int returned=0;
    while(pc<f->ncode){ Instr*in=&f->code[pc++]; const char*op=in->op;
        if(!strcmp(op,"PUSHI")){push(&st,vi(strtoll(in->a,NULL,10)));}
        else if(!strcmp(op,"PUSHB")){push(&st,vb(atoi(in->a)));}
        else if(!strcmp(op,"PUSHU")){push(&st,vu());}
        else if(!strcmp(op,"PUSHS")){char*s=unhex(in->a);push(&st,vt(s));free(s);}
        else if(!strcmp(op,"LOAD")){int x=atoi(in->a);if(x<0||x>=nloc)die("bad local");push(&st,clone(loc[x]));}
        else if(!strcmp(op,"STORE")){int x=atoi(in->a);if(x<0||x>=nloc)die("bad local");Value v=pop(&st);drop(loc[x]);loc[x]=v;}
        else if(!strcmp(op,"GLOAD")){int x=atoi(in->a);if(x<0||x>=p->nglobals)die("bad global");push(&st,clone(p->globals[x]));}
        else if(!strcmp(op,"GSTORE")){int x=atoi(in->a);if(x<0||x>=p->nglobals)die("bad global");Value v=pop(&st);drop(p->globals[x]);p->globals[x]=v;}
        else if(!strcmp(op,"POP")){drop(pop(&st));}
        else if(!strcmp(op,"DUP")){push(&st,clone(peek(&st)));}
        else if(!strcmp(op,"NEG")){Value a=pop(&st);if(a.k!=V_INT)die("NEG type");a.i=-a.i;push(&st,a);}
        else if(!strcmp(op,"NOT")){Value a=pop(&st);push(&st,vb(!truth(a)));drop(a);}
        else if(!strcmp(op,"ADD")||!strcmp(op,"SUB")||!strcmp(op,"MUL")||!strcmp(op,"DIV")||!strcmp(op,"MOD")){Value b=pop(&st),a=pop(&st);if(!strcmp(op,"ADD")&&a.k==V_TEXT&&b.k==V_TEXT){size_t x=strlen(a.s),y=strlen(b.s);char*s=xmalloc(x+y+1);memcpy(s,a.s,x);memcpy(s+x,b.s,y+1);drop(a);drop(b);push(&st,vt(s));free(s);}else{if(!((a.k==V_INT||a.k==V_BOOL)&&(b.k==V_INT||b.k==V_BOOL)))die("arithmetic type");int64_t z=0;if(!strcmp(op,"ADD"))z=a.i+b.i;else if(!strcmp(op,"SUB"))z=a.i-b.i;else if(!strcmp(op,"MUL"))z=a.i*b.i;else if(!strcmp(op,"DIV")){if(!b.i)die("division by zero");z=a.i/b.i;}else{if(!b.i)die("mod by zero");z=a.i%b.i;}drop(a);drop(b);push(&st,vi(z));}}
        else if(!strcmp(op,"EQ")||!strcmp(op,"NE")||!strcmp(op,"LT")||!strcmp(op,"LE")||!strcmp(op,"GT")||!strcmp(op,"GE")){Value b=pop(&st),a=pop(&st);int z=0;if(a.k==V_INT&&b.k==V_INT){if(!strcmp(op,"EQ"))z=a.i==b.i;else if(!strcmp(op,"NE"))z=a.i!=b.i;else if(!strcmp(op,"LT"))z=a.i<b.i;else if(!strcmp(op,"LE"))z=a.i<=b.i;else if(!strcmp(op,"GT"))z=a.i>b.i;else z=a.i>=b.i;}else if(a.k==V_TEXT&&b.k==V_TEXT){int c=strcmp(a.s,b.s);if(!strcmp(op,"EQ"))z=c==0;else if(!strcmp(op,"NE"))z=c!=0;else if(!strcmp(op,"LT"))z=c<0;else if(!strcmp(op,"LE"))z=c<=0;else if(!strcmp(op,"GT"))z=c>0;else z=c>=0;}else if(!strcmp(op,"EQ")||!strcmp(op,"NE")){z=(a.k==b.k&&a.i==b.i);if(!strcmp(op,"NE"))z=!z;}else die("comparison type");drop(a);drop(b);push(&st,vb(z));}
        else if(!strcmp(op,"JMP")){pc=label_pc(f,in->a);}
        else if(!strcmp(op,"JZ")){Value c=pop(&st);int z=truth(c);drop(c);if(!z)pc=label_pc(f,in->a);}
        else if(!strcmp(op,"CALL")){char*name=unhex(in->a);int n=atoi(in->b);Value*aa=xmalloc((size_t)n*sizeof(Value));for(int i=n-1;i>=0;i--)aa[i]=pop(&st);Func*g=find_func(p,name);if(!g){fprintf(stderr,"unknown function %s\n",name);exit(70);}Value r=exec_func(p,g,aa,n,host_argc,host_argv,depth+1);for(int i=0;i<n;i++)drop(aa[i]);free(aa);free(name);push(&st,r);}
        else if(!strcmp(op,"CALLB")){char*name=unhex(in->a);int n=atoi(in->b);Value*aa=xmalloc((size_t)n*sizeof(Value));for(int i=n-1;i>=0;i--)aa[i]=pop(&st);Value r=builtin(name,aa,n,host_argc,host_argv);for(int i=0;i<n;i++)drop(aa[i]);free(aa);free(name);push(&st,r);}
        else if(!strcmp(op,"MKLIST")){int n=atoi(in->a);Value r=vl();Value*aa=xmalloc((size_t)n*sizeof(Value));for(int i=n-1;i>=0;i--)aa[i]=pop(&st);for(int i=0;i<n;i++)list_add(r.l,aa[i]);free(aa);push(&st,r);}
        else if(!strcmp(op,"GETIDX")){Value idx=pop(&st),a=pop(&st);if(idx.k!=V_INT)die("index type");if(a.k==V_LIST){if(idx.i<0||(uint64_t)idx.i>=a.l->n){fprintf(stderr,"sh3vm: index range in %s pc=%zu idx=%" PRId64 " len=%zu\n",f->name,pc-1,idx.i,a.l->n);exit(70);}push(&st,clone(a.l->v[idx.i]));}else if(a.k==V_TEXT){size_t L=strlen(a.s);if(idx.i<0||(uint64_t)idx.i>=L){fprintf(stderr,"sh3vm: text index range in %s pc=%zu idx=%" PRId64 " len=%zu\n",f->name,pc-1,idx.i,L);exit(70);}char s[2]={a.s[idx.i],0};push(&st,vt(s));}else die("index receiver");drop(a);drop(idx);}
        else if(!strcmp(op,"SETIDX")){Value v=pop(&st),idx=pop(&st),a=pop(&st);if(a.k!=V_LIST||idx.k!=V_INT||idx.i<0||(uint64_t)idx.i>=a.l->n)die("setindex type/range");drop(a.l->v[idx.i]);a.l->v[idx.i]=clone(v);push(&st,a);drop(idx);drop(v);}
        else if(!strcmp(op,"PRINT")){Value a=pop(&st);char*s=value_text(a);fputs(s,stdout);fputc('\n',stdout);free(s);drop(a);push(&st,vu());}
        else if(!strcmp(op,"RET")){ret=st.n?pop(&st):vu();returned=1;break;}
        else {fprintf(stderr,"unknown opcode %s at source line %d\n",op,in->line);exit(70);}
    }
    if(!returned&&st.n)ret=pop(&st);
    for(size_t i=0;i<st.n;i++)drop(st.v[i]);
    free(st.v);
    for(int i=0;i<nloc;i++)drop(loc[i]);
    free(loc);
    return ret;
}
int main(int argc,char**argv){ if(argc<2){fprintf(stderr,"usage: sh3vm program.sbc [args...]\n");return 64;} Program p=load_program(argv[1]);Func*f=find_func(&p,p.entry);if(!f)die("entry not found");Value r=exec_func(&p,f,NULL,0,argc-2,argv+2,0);int rc=(r.k==V_INT)?(int)r.i:0;drop(r);free_program(&p);return rc;}
