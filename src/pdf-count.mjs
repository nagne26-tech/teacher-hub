// Count user-perceived characters; layout line breaks are not characters.
export function countText(text){
 const normalized=text.normalize('NFC').replace(/[\r\n\u2028\u2029]/gu,'');
 const segmenter=new Intl.Segmenter('ko',{granularity:'grapheme'});
 const count=value=>Array.from(segmenter.segment(value)).length;
 return {withSpaces:count(normalized),withoutSpaces:count(normalized.replace(/\s/gu,''))};
}
