// Snow by @akiro
// https://codepen.io/akiro/pen/YzvoWXV
// MIT license
$(document).ready(() => {
  var MAX_SNOW_SIZE = 7;
  var MAX_SNOW_SPEED = 1;
  snowStart();

  function snowStart() {
    createSnows();
  }

  function createSnows() {
    var container = $("#snow-animation-container");
    var MAX_SNOW = Math.round(Math.sqrt(
      container.width() * container.height() / 150
    ));
    console.log("// Snow animation start " + MAX_SNOW);
    for (var i = 0; i < MAX_SNOW; i++) {
      var appendItem = getRandomItem(i);
      container.append(appendItem);
      var animateItem = $(".snow" + String(i));
      var randomTime = Math.random() * MAX_SNOW_SPEED;
      goAnimate(animateItem, i, randomTime);
      goAnimate2(animateItem);
    }
    console.log("// Create snows");
  }

  function goAnimate(item, id, randomTime) {
    TweenMax.to(item, randomTime, {
      css: {marginTop: "+=100"}, ease: Linear.easeNone, onComplete: function () {
        var topPosition = item.css("margin-top").replace("px", "");
        if (topPosition > $(window).height()) {
          changePosition(item);
          randomTime = Math.random() * MAX_SNOW_SPEED;
          goAnimate(item, id, randomTime);
        } else {
          goAnimate(item, id, randomTime);
        }
      }
    });
  }

  function goAnimate2(item) {
    var directionTime = 1 + Math.floor(Math.random() * 5);
    var randomDirection = 1 + Math.floor(Math.random() * 4);
    var delayTime = 1 + Math.floor(Math.random() * 3);
    if (randomDirection == 1) {
      TweenMax.to(item, directionTime, {
        css: {marginLeft: "+=100"}, ease: Linear.easeOut, onComplete: function () {
          TweenMax.to(item, directionTime, {
            css: {marginLeft: "-=100"}, delay: delayTime, ease: Linear.easeOut, onComplete: function () {
              goAnimate2(item);
            }
          });
        }
      });
    } else if (randomDirection == 2) {
      TweenMax.to(item, directionTime, {
        css: {marginLeft: "-=100"}, ease: Linear.easeOut, onComplete: function () {
          TweenMax.to(item, directionTime, {
            css: {marginLeft: "+=100"}, delay: delayTime, ease: Linear.easeOut, onComplete: function () {
              goAnimate2(item);
            }
          });
        }
      });
    } else if (randomDirection == 3) {
      TweenMax.to(item, directionTime, {
        css: {marginLeft: "+=100"}, ease: Linear.easeOut, onComplete: function () {
          goAnimate2(item);
        }
      });
    } else if (randomDirection == 4) {
      TweenMax.to(item, directionTime, {
        css: {marginLeft: "-=100"}, ease: Linear.easeOut, onComplete: function () {
          goAnimate2(item);
        }
      });
    }
  }

  function changePosition(item) {
    var _width = Math.floor(Math.random() * MAX_SNOW_SIZE);
    var _height = _width;
    var _blur = Math.floor(Math.random() * 5 + 2);
    var _left = Math.floor(Math.random() * ($(window).width() - _width));
    var _top = -$(window).height() + Math.floor(Math.random() * ($(window).height() - _height));
    item.css("width", _width);
    item.css("height", _height);
    item.css("margin-left", _left);
    item.css("margin-top", _top);
    item.css("-webkit-filter", "blur(" + String(_blur) + "px)");
    item.css("-moz-filter", "blur(" + String(_blur) + "px)");
    item.css("-o-filter", "blur(" + String(_blur) + "px)");
    item.css("-ms-filter", "blur(" + String(_blur) + "px)");
    item.css("filter", "blur(" + String(_blur) + "px)");
  }

  function getRandomItem(id) {
    var _width = Math.floor(Math.random() * MAX_SNOW_SIZE);
    var _height = _width;
    var _blur = Math.floor(Math.random() * 5 + 2);
    var _left = Math.floor(Math.random() * ($(window).width() - _width));
    var _top = -$(window).height() + Math.floor(Math.random() * ($(window).height() - _height));
    var _id = id;
    return getSmallSnow(_width, _height, _blur, _left, _top, _id);
  }

  function getSmallSnow(width, height, blur, left, top, id) {
    var item = "<div class='snow" + id + "' style='position:absolute; margin-left: " + left + "px; margin-top: " + top + "px; width: " + width + "px; height: " + height + "px; border-radius: 50%; background-color: white; -webkit-filter: blur(" + blur + "px); -moz-filter: blur(" + blur + "px); -o-filter: blur(" + blur + "px); -ms-filter: blur(" + blur + "px); filter: blur(" + blur + "px);'></div>"
    return item;
  }
});