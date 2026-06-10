# Issues

再使用过程中发现 0.9.31 版本存在如下 bug，即在 dogent 执行过程中使用 ESC 键中断任务后，再次追加需求触发新任务，dogent 总是先失败一次。
日志如下，按 ESC 中断任务后，再要求执行，先会问是否需要记录 lesson，选择 no 之后，任务直接 Failed。然后再次提出要求，才能正常执行。

```
dogent> !ls
╭────────────────────────────────────────────────── ᯓ➤ Shell Result ───────────────────────────────────────────────────╮
│ $ ls                                                                                                                 │
│                                                                                                                      │
│ STDOUT:                                                                                                              │
│ 03-case-studies.docx                                                                                                 │
│ 03-case-studies.md                                                                                                   │
│ 03-case-studies.pdf                                                                                                  │
│                                                                                                                      │
│ Exit code: 0                                                                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
dogent> 总结下@03-case-studies.md 文件的内容
╭───────────────────────────────────────────────── 📂 File Reference ──────────────────────────────────────────────────╮
│ Referenced @03-case-studies.md                                                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────────────────────────────────────────────────── ⏳ Running ─────────────────────────────────────────────────────╮
│ Received request:                                                                                                    │
│ 总结下: 03-case-studies.md 文件的内容                                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────── 🤔 Thinking ─────────────────────────────────────────────────────╮
│ The user wants me to summarize the content of `03-case-studies.md`. Let me first read this file to understand its    │
│ content.                                                                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭────────────────────────────────────────────── ⚙️  dogent_read_document ───────────────────────────────────────────────╮
│ {'path': '03-case-studies.md'}                                                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Esc detected, interrupting the current task...
╭─────────────────────────────────────────────────── ⛔ Interrupted ───────────────────────────────────────────────────╮
│ Esc detected, interrupting the current task...                                                                       │
│ Remaining Todos: (none)                                                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
dogent> 重新继续总结下@03-case-studies.md 文件的内容
╭───────────────────────────────────────────────── 📂 File Reference ──────────────────────────────────────────────────╮
│ Referenced @03-case-studies.md                                                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
Save a lesson from the last failure/interrupt?

  yes
> no

Use ↑/↓ to select, Enter to confirm, Esc/Ctrl+C to cancel.
╭───────────────────────────────────────────────────── ⏳ Running ─────────────────────────────────────────────────────╮
│ Received request:                                                                                                    │
│ 重新继续总结下: 03-case-studies.md 文件的内容                                                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────────────────────────────────────────────────── ❌ Failed ──────────────────────────────────────────────────────╮
│ Result/Reason:                                                                                                       │
│ (no result returned)                                                                                                 │
│ Remaining Todos: (none)                                                                                              │
│ Duration 4787 ms | API 4187 ms | Cost $0.0787                                                                        │
│ Usage:                                                                                                               │
│ - Input tokens: 25833                                                                                                │
│ - Output tokens: 82                                                                                                  │
│ - Cache read tokens: 0                                                                                               │
│ - Cache creation tokens: 0                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
dogent>

```


此外，还发现，在使用 ECS 中断任务后，不退出 dogent，有的时候 dogent 会在命令行中吐错误信息 “Error in hook callback hook_0”，类似下面的日志：

```
Esc detected, interrupting the current task...
╭─────────────────────────────────────────────────── ⛔ Interrupted ───────────────────────────────────────────────────╮
│ Esc detected, interrupting the current task...                                                                       │
│ Remaining Todos:                                                                                                     │
│ - [in_progress] QA: Verify PPT content and visuals                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
dogent> Error in hook callback hook_0: 9212 | ${H.map((A)=>`- ${A.description||"(no description)"} (task ${A.task_id})`).join(`
9213 | `)}
9214 | Re-create them if still needed.
9215 | </system-reminder>`}var rw8=E(()=>{Q6();zX()});function DN7(H){return H.replace(ON7,(_)=>_==="\u2028"?"\\u2028":"\\u2029")}function ow8(H){return DN7(NH(H))}var ON7;var uu_=E(()=>{l6();ON7=/\u2028|\u2029/g});function YN7(H){if(!H)return;if(H.type==="classifier")return H.reason;switch(H.type){case"rule":case"mode":case"subcommandResults":case"permissionPromptTool":return;case"hook":case"asyncAgent":case"sandboxOverride":case"workingDir":case"safetyCheck":case"other":return H.reason}}function dvq(H,_){try{return H.getToolUseSummary?.(_)??H.getActivityDescription?.(_)??""}catch(A){return N(`describeToolUseForPush failed: ${A}`,{level:"error"}),""}}function wN7(H,_){if(!H.requiresUserInteraction?.())return;switch(H.name){case p5:{let A=Array.isArray(_?.questions)?_.questions:[],q=A[0],K=q?.header||q?.question,L=A.length>1?` (+${A.length-1} more)`:"";return{label:"Question",body:K?K+L:"Tap to answer"}}case wX:return{label:"Plan",body:"Plan ready for review"};default:return{label:KVH(H.name),body:""}}}function jN7( | ... truncated 
9216 | `)}async*read(){let H="",_=async function*(){for(;;){if(this.prependedLines.length>0)H=this.prependedLines.join("")+H,this.prependedLines=[];let A=H.indexOf(`
9217 | `)}async sendRequest(H,_,A,q=aw8.randomUUID()){let K={type:"control_request",request_id:q,request:H};if(this.inputClosed)throw Error("Stream closed");if(A?.aborted)throw Error("Request aborted");if(this.outbound.enqueue(K),H.subtype==="can_use_tool"&&this.onControlRequestSent)this.onControlRequestSent(K);let L=()=>{this.outbound.enqueue({type:"control_cancel_request",request_id:q});let M=this.pendingRequests.get(q);if(M)this.trackResolvedToolUseId(M.request),M.reject(new bf)};if(A)A.addEventListener("abort",L,{once:!0});let f=Date.now();try{return await new Promise((M,$)=>{this.pendingRequests.set(q,{request:{type:"control_request",request_id:q,request:H},resolve:(O)=>{M(O)},reject:$,schema:_})})}finally{if(Q("tengu_sdk_control_roundtrip",{subtype:H.subtype,duration_ms:Date.now()-f,aborted:A?.aborted??!1}),A)A.removeEventListener("abort",L);this.pendingRequests.delete(q)}}createCanUseTool(H){return async(_,A,q,K,L,f)=>{let M=f??await ew(_,A,q,K,L);if(M.behavior==="allow"||M.behavior==="deny")return M;let $=ne | ... truncated 

AbortError: 
      at L (/$bunfs/root/src/entrypoints/cli.js:9217:473)
      at f (/$bunfs/root/src/entrypoints/cli.js:2910:186)

Error in hook callback hook_0: 9212 | ${H.map((A)=>`- ${A.description||"(no description)"} (task ${A.task_id})`).join(`
9213 | `)}
9214 | Re-create them if still needed.
9215 | </system-reminder>`}var rw8=E(()=>{Q6();zX()});function DN7(H){return H.replace(ON7,(_)=>_==="\u2028"?"\\u2028":"\\u2029")}function ow8(H){return DN7(NH(H))}var ON7;var uu_=E(()=>{l6();ON7=/\u2028|\u2029/g});function YN7(H){if(!H)return;if(H.type==="classifier")return H.reason;switch(H.type){case"rule":case"mode":case"subcommandResults":case"permissionPromptTool":return;case"hook":case"asyncAgent":case"sandboxOverride":case"workingDir":case"safetyCheck":case"other":return H.reason}}function dvq(H,_){try{return H.getToolUseSummary?.(_)??H.getActivityDescription?.(_)??""}catch(A){return N(`describeToolUseForPush failed: ${A}`,{level:"error"}),""}}function wN7(H,_){if(!H.requiresUserInteraction?.())return;switch(H.name){case p5:{let A=Array.isArray(_?.questions)?_.questions:[],q=A[0],K=q?.header||q?.question,L=A.length>1?` (+${A.length-1} more)`:"";return{label:"Question",body:K?K+L:"Tap to answer"}}case wX:return{label:"Plan",body:"Plan ready for review"};default:return{label:KVH(H.name),body:""}}}function jN7( | ... truncated 
9216 | `)}async*read(){let H="",_=async function*(){for(;;){if(this.prependedLines.length>0)H=this.prependedLines.join("")+H,this.prependedLines=[];let A=H.indexOf(`
9217 | `)}async sendRequest(H,_,A,q=aw8.randomUUID()){let K={type:"control_request",request_id:q,request:H};if(this.inputClosed)throw Error("Stream closed");if(A?.aborted)throw Error("Request aborted");if(this.outbound.enqueue(K),H.subtype==="can_use_tool"&&this.onControlRequestSent)this.onControlRequestSent(K);let L=()=>{this.outbound.enqueue({type:"control_cancel_request",request_id:q});let M=this.pendingRequests.get(q);if(M)this.trackResolvedToolUseId(M.request),M.reject(new bf)};if(A)A.addEventListener("abort",L,{once:!0});let f=Date.now();try{return await new Promise((M,$)=>{this.pendingRequests.set(q,{request:{type:"control_request",request_id:q,request:H},resolve:(O)=>{M(O)},reject:$,schema:_})})}finally{if(Q("tengu_sdk_control_roundtrip",{subtype:H.subtype,duration_ms:Date.now()-f,aborted:A?.aborted??!1}),A)A.removeEventListener("abort",L);this.pendingRequests.delete(q)}}createCanUseTool(H){return async(_,A,q,K,L,f)=>{let M=f??await ew(_,A,q,K,L);if(M.behavior==="allow"||M.behavior==="deny")return M;let $=ne | ... truncated 

AbortError: 
      at L (/$bunfs/root/src/entrypoints/cli.js:9217:473)
      at f (/$bunfs/root/src/entrypoints/cli.js:2910:186)

Error in hook callback hook_0: 9212 | ${H.map((A)=>`- ${A.description||"(no description)"} (task ${A.task_id})`).join(`
9213 | `)}
9214 | Re-create them if still needed.
9215 | </system-reminder>`}var rw8=E(()=>{Q6();zX()});function DN7(H){return H.replace(ON7,(_)=>_==="\u2028"?"\\u2028":"\\u2029")}function ow8(H){return DN7(NH(H))}var ON7;var uu_=E(()=>{l6();ON7=/\u2028|\u2029/g});function YN7(H){if(!H)return;if(H.type==="classifier")return H.reason;switch(H.type){case"rule":case"mode":case"subcommandResults":case"permissionPromptTool":return;case"hook":case"asyncAgent":case"sandboxOverride":case"workingDir":case"safetyCheck":case"other":return H.reason}}function dvq(H,_){try{return H.getToolUseSummary?.(_)??H.getActivityDescription?.(_)??""}catch(A){return N(`describeToolUseForPush failed: ${A}`,{level:"error"}),""}}function wN7(H,_){if(!H.requiresUserInteraction?.())return;switch(H.name){case p5:{let A=Array.isArray(_?.questions)?_.questions:[],q=A[0],K=q?.header||q?.question,L=A.length>1?` (+${A.length-1} more)`:"";return{label:"Question",body:K?K+L:"Tap to answer"}}case wX:return{label:"Plan",body:"Plan ready for review"};default:return{label:KVH(H.name),body:""}}}function jN7( | ... truncated 
9216 | `)}async*read(){let H="",_=async function*(){for(;;){if(this.prependedLines.length>0)H=this.prependedLines.join("")+H,this.prependedLines=[];let A=H.indexOf(`
9217 | `)}async sendRequest(H,_,A,q=aw8.randomUUID()){let K={type:"control_request",request_id:q,request:H};if(this.inputClosed)throw Error("Stream closed");if(A?.aborted)throw Error("Request aborted");if(this.outbound.enqueue(K),H.subtype==="can_use_tool"&&this.onControlRequestSent)this.onControlRequestSent(K);let L=()=>{this.outbound.enqueue({type:"control_cancel_request",request_id:q});let M=this.pendingRequests.get(q);if(M)this.trackResolvedToolUseId(M.request),M.reject(new bf)};if(A)A.addEventListener("abort",L,{once:!0});let f=Date.now();try{return await new Promise((M,$)=>{this.pendingRequests.set(q,{request:{type:"control_request",request_id:q,request:H},resolve:(O)=>{M(O)},reject:$,schema:_})})}finally{if(Q("tengu_sdk_control_roundtrip",{subtype:H.subtype,duration_ms:Date.now()-f,aborted:A?.aborted??!1}),A)A.removeEventListener("abort",L);this.pendingRequests.delete(q)}}createCanUseTool(H){return async(_,A,q,K,L,f)=>{let M=f??await ew(_,A,q,K,L);if(M.behavior==="allow"||M.behavior==="deny")return M;let $=ne | ... truncated 

AbortError: 
      at L (/$bunfs/root/src/entrypoints/cli.js:9217:473)
      at f (/$bunfs/root/src/entrypoints/cli.js:2910:186)

Error in hook callback hook_0: 9212 | ${H.map((A)=>`- ${A.description||"(no description)"} (task ${A.task_id})`).join(`
9213 | `)}
9214 | Re-create them if still needed.

```