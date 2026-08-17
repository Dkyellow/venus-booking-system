// Hamburger
(function(){
  var hamburger=document.getElementById('hpHamburger');
  var menu=document.getElementById('hpMobileMenu');
  if(hamburger&&menu){
    hamburger.addEventListener('click',function(){
      menu.classList.toggle('show');
      var icon=hamburger.querySelector('i');
      if(menu.classList.contains('show')){
        icon.classList.remove('fa-bars');icon.classList.add('fa-times');
        hamburger.style.transform='rotate(90deg)';
      }else{
        icon.classList.remove('fa-times');icon.classList.add('fa-bars');
        hamburger.style.transform='rotate(0deg)';
      }
    });
    document.querySelectorAll('#hpMobileMenu .nav-link').forEach(function(a){
      a.addEventListener('click',function(){
        menu.classList.remove('show');
        hamburger.style.transform='rotate(0deg)';
      });
    });
  }
})();

// Smooth scroll for same-page anchors
document.querySelectorAll('a[href^="#"]').forEach(function(a){
  a.addEventListener('click',function(e){
    var t=document.querySelector(this.getAttribute('href'));
    if(t){e.preventDefault();t.scrollIntoView({behavior:'smooth',block:'start'})}
  });
});

// Nav scroll effect
var lastScroll=0;
var hpNav=document.querySelector('.hp-nav');
if(hpNav){
  window.addEventListener('scroll',function(){
    var nav=document.querySelector('.hp-nav');
    var scrollY=window.scrollY;
    if(scrollY>50){nav.classList.add('scrolled')}
    else{nav.classList.remove('scrolled')}
    if(scrollY>lastScroll&&scrollY>100){nav.style.transform='translateY(-100%)'}
    else{nav.style.transform='translateY(0)'}
    lastScroll=scrollY;
  });
}

// Scroll animations with stagger
function homeAnimateOnScroll(){
  var elements=document.querySelectorAll('.animate-on-scroll');
  elements.forEach(function(el){
    var rect=el.getBoundingClientRect();
    if(rect.top<window.innerHeight-60){el.classList.add('visible')}
  });
}
window.addEventListener('scroll',homeAnimateOnScroll);
window.addEventListener('load',homeAnimateOnScroll);

// Add animate-on-scroll to cards with stagger
document.addEventListener('DOMContentLoaded',function(){
  var animGroups=[
    {sel:'.feature-card',delay:0.1},
    {sel:'.service-home-card',delay:0.08},
    {sel:'.service-chip',delay:0.08},
    {sel:'.how-step',delay:0.15},
    {sel:'.team-card',delay:0.15},
    {sel:'.gallery-section .row > div',delay:0.1},
    {sel:'.faq-section .accordion-item',delay:0.08},
    {sel:'.stats-bar-item',delay:0.1},
    {sel:'.contact-section > .container > .row > div',delay:0.2}
  ];
  animGroups.forEach(function(group){
    document.querySelectorAll(group.sel).forEach(function(el,i){
      el.classList.add('animate-on-scroll');
      el.style.transitionDelay=(i*group.delay)+'s';
    });
  });
  homeAnimateOnScroll();
  // Re-run after a tick to catch elements revealed by IntersectionObserver/revealVisible
  setTimeout(homeAnimateOnScroll, 100);
  setTimeout(homeAnimateOnScroll, 400);
});

// Counter animation for stats
function homeAnimateCounters(){
  var counters=document.querySelectorAll('.hero-stat-num, .stats-bar-num');
  counters.forEach(function(counter){
    if(counter.dataset.animated) return;
    var rect=counter.getBoundingClientRect();
    if(rect.top<window.innerHeight){
      counter.dataset.animated='true';
      var text=counter.textContent;
      var match=text.match(/(\d+)/);
      if(match){
        var target=parseInt(match[1]);
        var suffix=text.replace(match[1],'');
        var current=0;
        var increment=Math.ceil(target/40);
        var timer=setInterval(function(){
          current+=increment;
          if(current>=target){current=target;clearInterval(timer)}
          counter.textContent=current+suffix;
        },25);
      }
    }
  });
}
window.addEventListener('scroll',homeAnimateCounters);
window.addEventListener('load',homeAnimateCounters);

// Image lazy load with fade
document.querySelectorAll('img').forEach(function(img){
  img.style.transition='opacity 0.6s ease, transform 0.6s ease';
  img.style.opacity='0';
  img.addEventListener('load',function(){this.style.opacity='1'});
  if(img.complete&&img.naturalHeight!==0){img.style.opacity='1'}
});

// Ripple effect on buttons
document.querySelectorAll('.btn-hero, .btn-nav, .team-card a').forEach(function(btn){
  btn.addEventListener('click',function(e){
    var ripple=document.createElement('span');
    ripple.style.cssText='position:absolute;border-radius:50%;background:rgba(255,255,255,0.4);transform:scale(0);animation:ripple 0.6s linear;pointer-events:none';
    var rect=this.getBoundingClientRect();
    var size=Math.max(rect.width,rect.height);
    ripple.style.width=ripple.style.height=size+'px';
    ripple.style.left=(e.clientX-rect.left-size/2)+'px';
    ripple.style.top=(e.clientY-rect.top-size/2)+'px';
    this.style.position='relative';this.style.overflow='hidden';
    this.appendChild(ripple);
    setTimeout(function(){ripple.remove()},600);
  });
});

// Ripple keyframe
(function(){
  var style=document.createElement('style');
  style.textContent='@keyframes ripple{to{transform:scale(4);opacity:0}}';
  document.head.appendChild(style);
})();

// Parallax on hero
window.addEventListener('scroll',function(){
  var hero=document.querySelector('.hero');
  if(hero&&window.innerWidth>768&&hero.style.backgroundImage!=='none'&&getComputedStyle(hero).backgroundImage.indexOf('url')>-1){
    var scrolled=window.scrollY;
    hero.style.backgroundPositionY=scrolled*0.5+'px';
  }
});

// Tilt effect on cards
document.querySelectorAll('.feature-card, .team-card').forEach(function(card){
  card.addEventListener('mousemove',function(e){
    var rect=this.getBoundingClientRect();
    var x=e.clientX-rect.left;
    var y=e.clientY-rect.top;
    var centerX=rect.width/2;
    var centerY=rect.height/2;
    var rotateX=(y-centerY)/20;
    var rotateY=(centerX-x)/20;
    this.style.transform='perspective(1000px) rotateX('+rotateX+'deg) rotateY('+rotateY+'deg) translateY(-8px)';
  });
  card.addEventListener('mouseleave',function(){
    this.style.transform='perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0)';
  });
});

// Smooth reveal for sections
(function(){
  var observer=new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if(entry.isIntersecting){
        entry.target.style.opacity='1';
        entry.target.style.transform='translateY(0)';
      }
    });
  },{threshold:0,rootMargin:'0px 0px -30px 0px'});
  document.querySelectorAll('section').forEach(function(sec){
    sec.style.opacity='0';
    sec.style.transform='translateY(30px)';
    sec.style.transition='all 0.8s cubic-bezier(0.4,0,0.2,1)';
    observer.observe(sec);
  });
  // Immediately show any sections already visible in the viewport on load
  function revealVisible(){
    document.querySelectorAll('section').forEach(function(sec){
      var rect=sec.getBoundingClientRect();
      if(rect.top<window.innerHeight&&rect.bottom>0){
        sec.style.opacity='1';
        sec.style.transform='translateY(0)';
      }
    });
  }
  revealVisible();
  window.addEventListener('load',revealVisible);
})();