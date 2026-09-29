```javascript
document.addEventListener("DOMContentLoaded", function () {

    /*
     * Automatically hide alert messages
     * after 5 seconds.
     */

    setTimeout(function () {

        const alerts = document.querySelectorAll(
            ".alert"
        );

        alerts.forEach(function (alert) {

            const closeButton =
                alert.querySelector(".btn-close");

            if (closeButton) {
                closeButton.click();
            }

        });

    }, 5000);

});
```
