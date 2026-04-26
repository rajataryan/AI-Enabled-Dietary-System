import './async-D55cHugf.js';
import { a as attr, g as attr_style, d as bind_props, c as spread_props } from './index-u8mz_F03.js';
import './2-EyCg4N-O.js';
import { $ } from './utils.svelte-C798QV9b.js';
import { s } from './tinycolor-DfhFic3A.js';
import { c } from './BlockTitle-BnJIYf6a.js';
import { G } from './Block-DZmzQwnI.js';
import { W } from './index3-Rp9AmCmX.js';
export { default as BaseExample } from './Example13-cXK-YGz2.js';
import { e as escape_html } from './escaping-CBnpiEl5.js';
import './context-CBkBucIx.js';
import './index5-BoOEKc6P.js';
import './dev-fallback-Bc5Ork7Y.js';
import './index-Cg-Pg6j3.js';
import './clone-Yk88IHKV.js';
import './Info-DU6zbiUl.js';
import './html-CfyvkLET.js';
import './IconButton-BRnu7KaR.js';
import './Clear-D7Yjckqz.js';

function w(e,a){return s(e).toHexString()}function B(e,a){e.component(t=>{let{value:i=void 0,label:c$1,info:u,disabled:o,show_label:p,on_input:r=()=>{},on_submit:n=()=>{},on_blur:d=()=>{},on_focus:m=()=>{}}=a;w(i),c(t,{show_label:p,info:u,children:s=>{s.push(`<!---->${escape_html(c$1)}`);},$$slots:{default:true}}),t.push(`<!----> <button class="dialog-button svelte-nbn1m9"${attr("disabled",o,true)}${attr_style("",{background:i})}></button> `),t.push("<!--[!-->"),t.push("<!--]-->"),bind_props(a,{value:i});});}function j(e,a){e.component(t=>{let{$$slots:i,$$events:c,...u}=a;const o=new $(u,{value:"#000000"});o.props.value;let p=o.shared.label||o.i18n("color_picker.color_picker"),r=true,n;function d(m){G(m,{visible:o.shared.visible,elem_id:o.shared.elem_id,elem_classes:o.shared.elem_classes,container:o.shared.container,scale:o.shared.scale,min_width:o.shared.min_width,children:s=>{W(s,spread_props([{autoscroll:o.shared.autoscroll,i18n:o.i18n},o.shared.loading_status,{on_clear_status:()=>o.dispatch("clear_status",o.shared.loading_status)}])),s.push("<!----> "),B(s,{label:p,info:o.props.info,show_label:o.shared.show_label,disabled:!o.shared.interactive,on_input:()=>o.dispatch("input"),on_submit:()=>o.dispatch("submit"),on_blur:()=>o.dispatch("blur"),on_focus:()=>o.dispatch("focus"),get value(){return o.props.value},set value(h){o.props.value=h,r=false;}}),s.push("<!---->");},$$slots:{default:true}});}do r=true,n=t.copy(),d(n);while(!r);t.subsume(n);});}

export { B as BaseColorPicker, j as default };
//# sourceMappingURL=Index40-CRYY9C5D.js.map
