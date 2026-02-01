// WinAdapter.h - Compatibility layer for non-Windows platforms
// Provides SAL (Source Annotation Language) macros as empty definitions

#pragma once

#ifndef _WIN32

// SAL annotations - empty definitions for non-Windows
#ifndef _In_
#define _In_
#endif
#ifndef _In_opt_
#define _In_opt_
#endif
#ifndef _Out_
#define _Out_
#endif
#ifndef _Out_opt_
#define _Out_opt_
#endif
#ifndef _Inout_
#define _Inout_
#endif
#ifndef _Inout_opt_
#define _Inout_opt_
#endif
#ifndef _In_reads_
#define _In_reads_(x)
#endif
#ifndef _In_reads_opt_
#define _In_reads_opt_(x)
#endif
#ifndef _In_reads_bytes_
#define _In_reads_bytes_(x)
#endif
#ifndef _Out_writes_
#define _Out_writes_(x)
#endif
#ifndef _Out_writes_opt_
#define _Out_writes_opt_(x)
#endif
#ifndef _Out_writes_bytes_
#define _Out_writes_bytes_(x)
#endif
#ifndef _Inout_updates_
#define _Inout_updates_(x)
#endif
#ifndef _Inout_updates_bytes_
#define _Inout_updates_bytes_(x)
#endif
#ifndef _Out_writes_to_
#define _Out_writes_to_(x, y)
#endif
#ifndef _Analysis_assume_
#define _Analysis_assume_(x)
#endif
#ifndef _Use_decl_annotations_
#define _Use_decl_annotations_
#endif
#ifndef _Success_
#define _Success_(x)
#endif
#ifndef _Pre_notnull_
#define _Pre_notnull_
#endif
#ifndef _Null_terminated_
#define _Null_terminated_
#endif
#ifndef _Printf_format_string_
#define _Printf_format_string_
#endif

// Additional SAL macros
#ifndef __in
#define __in
#endif
#ifndef __out
#define __out
#endif
#ifndef __inout
#define __inout
#endif
#ifndef __in_opt
#define __in_opt
#endif
#ifndef __out_opt
#define __out_opt
#endif
#ifndef __in_ecount
#define __in_ecount(x)
#endif
#ifndef __out_ecount
#define __out_ecount(x)
#endif
#ifndef __in_bcount
#define __in_bcount(x)
#endif
#ifndef __out_bcount
#define __out_bcount(x)
#endif

#endif // !_WIN32
