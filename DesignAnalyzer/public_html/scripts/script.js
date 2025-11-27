
// Toggle main menu visibility
const burger = document.getElementById('burger');
const menu = document.getElementById('menuItems');

if(burger) {
  burger.addEventListener('click', () => {
    menu.classList.toggle('active');
    const expanded = menu.classList.contains('active');
    menu.setAttribute('aria-expanded', expanded);
  });
}

// Toggle submenu on menu item click
document.querySelectorAll('.menu-item').forEach(item => {
  item.addEventListener('click', (e) => {
    // Avoid toggling submenu when clicking links inside submenu
    if (e.target.tagName.toLowerCase() === 'a') return;

    // Toggle submenu open class
    item.classList.toggle('open');

    // Accessibility: toggle aria-hidden for submenu
    const submenu = item.querySelector('.submenu');
    if(submenu) {
      const isOpen = item.classList.contains('open');
      submenu.setAttribute('aria-hidden', !isOpen);
    }
  });
});

document.addEventListener('click', (e) => {
  const menu = document.getElementById('menuItems');
  const burger = document.getElementById('burger');
  const navMenu = document.getElementById('navMenu');

  if (menu.classList.contains('active')) {
    // If click is NOT inside navMenu (burger or menu-items), close menu
    if (!navMenu.contains(e.target)) {
      menu.classList.remove('active');
      menu.setAttribute('aria-expanded', false);
      
      // Also close all open submenus
      document.querySelectorAll('.menu-item.open').forEach(item => {
        item.classList.remove('open');
        const submenu = item.querySelector('.submenu');
        if(submenu) submenu.setAttribute('aria-hidden', true);
      });
    }
  }
});

// Optional: allow keyboard toggle with Enter or Space
document.querySelectorAll('.menu-item, #burger').forEach(el => {
  el.addEventListener('keydown', e => {
    if(e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      el.click();
    }
  });
});

    const submenuMap = {
      solution: [
        { text: "Integrated AI", href: "analytics.html#Integrated-AI" },
        { text: "Visualization", href: "analytics.html#Visualization" },
        { text: "Performance & Capacity", href: "analytics.html#Performance" }
      ],
      products: [
        { text: "Analyzerr", href: "analytics.html#Analyzerr" }
      ],
      Education: [
        { text: "Our Approach", href: "education_consultancy.html#Approach" },
        { text: "Our Deliverables", href: "education_consultancy.html#Deliverables" }
      ],
      Travel: [
        { text: "Our Approach", href: "travel_consultancy.html#Approach" },
        { text: "Our Deliverables", href: "travel_consultancy.html#Deliverables" }
      ],
    };


  const menuItems = document.querySelectorAll('.menu-item');
  const sharedSubmenu = document.getElementById('sharedSubmenu');

  menuItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation(); // prevent from triggering document click

      const key = item.getAttribute('data-menu');
      const items = submenuMap[key] || [];

      // Build submenu content
      sharedSubmenu.innerHTML = items.map(entry =>
        `<a href="${entry.href}">${entry.text}</a>`
      ).join('');

      sharedSubmenu.classList.add('active');
    });
  });

  // Hide submenu when clicking outside
  document.addEventListener('click', () => {
    sharedSubmenu.classList.remove('active');
  });

if (sharedSubmenu) {
  // Prevent click inside submenu from closing it
  sharedSubmenu.addEventListener('click', (e) => {
    e.stopPropagation();
  });
}




