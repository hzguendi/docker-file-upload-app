document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeLabel = document.querySelector('.theme-label');
    
    // Check if theme is stored in localStorage
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeToggle.checked = true;
        themeLabel.textContent = 'Light Mode';
    }
    
    // Toggle theme when switch is clicked
    themeToggle.addEventListener('change', function() {
        if (this.checked) {
            // Dark mode
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            themeLabel.textContent = 'Dark Mode';
        } else {
            // Light mode
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
            themeLabel.textContent = 'Light Mode';
        }
    });
});