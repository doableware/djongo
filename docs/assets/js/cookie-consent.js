// A $( document ).ready() block.
$( document ).ready(function() {
    const cookieName = 'user-cookie-consent';
    let hasConsented = Cookies.get(cookieName);

    if(hasConsented === 'true') {
       $(".cookie-notice").css('display', 'none');
    }

    $("#cookie-accept").click(function () {
        $(".cookie-notice").css('display', 'none');
        Cookies.set(cookieName, 'true');
    })
});