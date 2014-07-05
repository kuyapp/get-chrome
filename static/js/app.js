// select url text
$(document).on('mouseenter', 'pre', function() {
  var doc = document
    , text = $(this).find('code')
    , range, selection;

  if(!text.length) return;

  text = text[0];

  // http://stackoverflow.com/a/987376/1189321
  if (doc.body.createTextRange) {
    range = doc.body.createTextRange();
    range.moveToElementText(text);
    range.select();
  } else if (window.getSelection) {
    selection = window.getSelection();
    range = doc.createRange();
    range.selectNodeContents(text);
    selection.removeAllRanges();
    selection.addRange(range);
  }
});