/*!
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

/*! For license information please see dag.0acb51e196647f5984f7.js.LICENSE.txt */
!function(e,t){"object"==typeof exports&&"object"==typeof module?module.exports=t():"function"==typeof define&&define.amd?define([],t):"object"==typeof exports?exports.Airflow=t():(e.Airflow=e.Airflow||{},e.Airflow.dag=t())}(self,(()=>(()=>{"use strict";var e={1068:(e,t,a)=>{a.d(t,{K5:()=>o,o0:()=>d});const n="YYYY-MM-DD, HH:mm:ss z";const d=e=>moment(e).format(n);const o=e=>`${moment(e).fromNow()}`},8956:(e,t,a)=>{a.d(t,{au:()=>n});function n(e){const t=document.querySelector(`meta[name="${e}"]`);return t?t.getAttribute("content"):null}}},t={};function a(n){var d=t[n];if(void 0!==d)return d.exports;var o=t[n]={exports:{}};return e[n](o,o.exports,a),o.exports}a.d=(e,t)=>{for(var n in t)a.o(t,n)&&!a.o(e,n)&&Object.defineProperty(e,n,{enumerable:!0,get:t[n]})},a.o=(e,t)=>Object.prototype.hasOwnProperty.call(e,t),a.r=e=>{"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})};var n={};return(()=>{a.r(n),a.d(n,{callModal:()=>w,dagTZ:()=>o});var e=a(8956),t=a(1068);$(window).on("load",(function(){$(`a[href*="${this.location.pathname}"]`).parent().addClass("active"),$(".never_active").removeClass("active")}));const d=(0,e.au)("dag_id"),o=(0,e.au)("dag_timezone"),i=(0,e.au)("logs_with_metadata_url"),r=(0,e.au)("external_log_url"),l=(0,e.au)("extra_links_url"),s=(0,e.au)("paused_url"),_={createAfter:(0,e.au)("next_dagrun_create_after"),intervalStart:(0,e.au)("next_dagrun_data_interval_start"),intervalEnd:(0,e.au)("next_dagrun_data_interval_end")};let p,c="",u="",m="",x="",g=[];const f="True"===(0,e.au)("show_external_log_redirect"),h=Array.from(document.querySelectorAll('a[id^="btn_"][data-base-url]')).reduce(((e,t)=>(e[t.id.replace("btn_","")]=t,e)),{});function b(e,t){let a=e.dataset.baseUrl;t.dag_id&&-1!==e.dataset.baseUrl.indexOf(d)&&(a=a.replace(d,t.dag_id),delete t.dag_id),Object.prototype.hasOwnProperty.call(t,"map_index")&&void 0===t.map_index&&delete t.map_index,e.setAttribute("href",`${a}?${$.param(t)}`)}function v(){b(h.subdag,{dag_id:m,execution_date:u}),b(h.task,{dag_id:d,task_id:c,execution_date:u,map_index:p}),b(h.rendered,{dag_id:d,task_id:c,execution_date:u,map_index:p}),b(h.mapped,{_flt_3_dag_id:d,_flt_3_task_id:c,_flt_3_run_id:x,_oc_TaskInstanceModelView:"map_index"}),h.rendered_k8s&&b(h.rendered_k8s,{dag_id:d,task_id:c,execution_date:u,map_index:p});const e={_flt_3_dag_id:d,_flt_3_task_id:c,_oc_TaskInstanceModelView:"dag_run.execution_date"};p>=0&&(e._flt_0_map_index=p),b(h.ti,e),b(h.log,{dag_id:d,task_id:c,execution_date:u,map_index:p}),b(h.xcom,{dag_id:d,task_id:c,execution_date:u,map_index:p})}function w({taskId:e,executionDate:a,extraLinks:n,tryNumber:o,isSubDag:s,dagRunId:_,mapIndex:h,isMapped:b=!1,mappedStates:w=[]}){c=e;const k=String(window.location);if($("#btn_filter").on("click",(()=>{window.location=function(e,t,a){const n=new RegExp(`([?&])${t}=.*?(&|$)`,"i"),d=-1!==e.indexOf("?")?"&":"?";return e.match(n)?e.replace(n,`$1${t}=${a}$2`):`${e}${d}${t}=${a}`}(k,"root",c)})),u=a,x=_,p=h,b&&(g=w),$("#dag_run_id").text(_),$("#task_id").text(e),$("#execution_date").text((0,t.o0)(a)),$("#taskInstanceModal").modal({}),$("#taskInstanceModal").css("margin-top","0"),$("#extra_links").prev("hr").hide(),$("#extra_links").empty().hide(),h>=0?($("#modal_map_index").show(),$("#modal_map_index .value").text(h)):($("#modal_map_index").hide(),$("#modal_map_index .value").text("")),s?($("#div_btn_subdag").show(),m=`${d}.${e}`):($("#div_btn_subdag").hide(),m=void 0),h>=0&&!g.length)$("#modal_map_index").show(),$("#modal_map_index .value").text(h),$("#mapped_dropdown").hide();else if(h>=0||b){$("#modal_map_index").show(),$("#modal_map_index .value").text(""),$("#mapped_dropdown").show();const e=p>-1?p:`All  ${g.length} Mapped Instances`;$("#mapped_dropdown #dropdown-label").text(e),$("#mapped_dropdown .dropdown-menu").empty(),$("#mapped_dropdown .dropdown-menu").append(`<li><a href="#" class="map_index_item" data-mapIndex="all">All ${g.length} Mapped Instances</a></li>`),g.forEach(((e,t)=>{$("#mapped_dropdown .dropdown-menu").append(`<li><a href="#" class="map_index_item" data-mapIndex="${t}">${t} - ${e}</a></li>`)}))}else $("#modal_map_index").hide(),$("#modal_map_index .value").text(""),$("#mapped_dropdown").hide();b?($("#task_actions").text(`Task Actions for all ${w.length} instances`),$("#btn_mapped").show(),$("#mapped_dropdown").css("display","inline-block"),$("#btn_rendered").hide(),$("#btn_xcom").hide(),$("#btn_log").hide(),$("#btn_task").hide()):($("#task_actions").text("Task Actions"),$("#btn_rendered").show(),$("#btn_xcom").show(),$("#btn_log").show(),$("#btn_mapped").hide(),$("#btn_task").show()),$("#dag_dl_logs").hide(),$("#dag_redir_logs").hide(),o>0&&!b&&($("#dag_dl_logs").show(),f&&$("#dag_redir_logs").show()),v(),$("#try_index > li").remove(),$("#redir_log_try_index > li").remove();const y=o>2?0:1,I=new URLSearchParams({dag_id:d,task_id:c,execution_date:u,metadata:"null"});void 0!==h&&I.set("map_index",h);for(let e=y;e<o;e+=1){let t=e;0!==e?I.set("try_number",e):t="All",$("#try_index").append(`<li role="presentation" style="display:inline">\n      <a href="${i}?${I}&format=file"> ${t} </a>\n      </li>`),(0!==e||f)&&$("#redir_log_try_index").append(`<li role="presentation" style="display:inline">\n      <a href="${r}?${I}"> ${t} </a>\n      </li>`)}if(I.delete("try_number"),n&&n.length>0){const e=[];n.sort(),$.each(n,((t,a)=>{I.set("link_name",a);const n=$('<a href="#" class="btn btn-primary disabled"></a>'),d=$('<span class="tool-tip" data-toggle="tooltip" style="padding-right: 2px; padding-left: 3px" data-placement="top" title="link not yet available"></span>');d.append(n),n.text(a),$.ajax({url:`${l}?${I}`,cache:!1,success(e){n.attr("href",e.url),/^(?:[a-z]+:)?\/\//.test(e.url)&&n.attr("target","_blank"),n.removeClass("disabled"),d.tooltip("disable")},error(e){d.tooltip("hide").attr("title",e.responseJSON.error).tooltip("fixTitle")}}),e.push(d)}));const t=$("#extra_links");t.prev("hr").show(),t.append(e).show(),t.find('[data-toggle="tooltip"]').tooltip()}}document.addEventListener("click",(e=>{e.target.matches('button[data-toggle="button"]')&&v()})),$(document).on("click",".map_index_item",(function(){const e=$(this).attr("data-mapIndex");w("all"===e?{taskId:c,executionDate:u,dagRunId:x,mapIndex:-1,isMapped:!0,mappedStates:g}:{taskId:c,executionDate:u,dagRunId:x,mapIndex:e})})),$("form[data-action]").on("submit",(function(e){e.preventDefault();const t=$(this).get(0);(x||u)&&(t.dag_run_id&&(t.dag_run_id.value=x),t.execution_date&&(t.execution_date.value=u),t.origin.value=window.location,t.task_id&&(t.task_id.value=c),t.map_index&&p>=0?t.map_index.value=p:t.map_index&&t.map_index.remove(),t.action=$(this).data("action"),t.submit())})),$("#pause_resume").on("change",(function(){const e=$(this),t=e.data("dag-id"),a=e.is(":checked"),n=`${s}?is_paused=${a}&dag_id=${encodeURIComponent(t)}`;e.trigger("blur"),e.removeClass("switch-input--error");const d=new CustomEvent("paused",{detail:a});document.dispatchEvent(d),$.post(n).fail((()=>{setTimeout((()=>{e.prop("checked",!a),e.addClass("switch-input--error"),d.value=!a,document.dispatchEvent(d)}),500)}))})),$("#next-run").on("mouseover",(()=>{$("#next-run").attr("data-original-title",(()=>{let e="";return _.createAfter&&(e+=`<strong>Run After:</strong> ${(0,t.o0)(_.createAfter)}<br>`,e+=`Next Run: ${(0,t.K5)(_.createAfter)}<br><br>`),_.intervalStart&&_.intervalEnd&&(e+="<strong>Data Interval</strong><br>",e+=`Start: ${(0,t.o0)(_.intervalStart)}<br>`,e+=`End: ${(0,t.o0)(_.intervalEnd)}`),e}))}))})(),n})()));
