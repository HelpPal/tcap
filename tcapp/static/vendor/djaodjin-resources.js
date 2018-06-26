/* Copyright (c) 2016, DjaoDjin inc.
   All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions are met:

  1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.
  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
  TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
  PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
  CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
  WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
  OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
  ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/


/** These are plumbing functions to connect the UI and API backends.
 */

function showMessages(messages, style) {
    "use strict";
    if( typeof toastr !== 'undefined' ) {
        for( var i = 0; i < messages.length; ++i ) {
            toastr[style](messages[i]);
        }

    } else {
        var messageBlock = "<div class=\"alert alert-block";
        if( style ) {
            if( style === "error" ) {
                style = "danger";
            }
            messageBlock += " alert-" + style;
        }
        messageBlock += "\"><button type=\"button\" class=\"close\" data-dismiss=\"alert\">&times;</button>";

        for( var i = 0; i < messages.length; ++i ) {
            messageBlock += "<div>" + messages[i] + "</div>";
         }
         messageBlock += "</div>";
         $("#messages-content").append(messageBlock);
    }
    $("#messages").removeClass("hidden");
    $("html, body").animate({
        // scrollTop: $("#messages").offset().top - 50
        // avoid weird animation when messages at the top:
        scrollTop: $("body").offset().top
    }, 500);
}


function showErrorMessages(resp) {
    var messages = [];
    if( typeof resp === "string" ) {
        messages = [resp];
    } else {
        if( resp.data && typeof resp.data === "object" ) {
            for( var key in resp.data ) {
                if (resp.data.hasOwnProperty(key)) {
                    var message = resp.data[key];
                    if( typeof resp.data[key] !== 'string' ) {
                        message = "";
                        var sep = "";
                        for( var i = 0; i < resp.data[key].length; ++i ) {
                            var messagePart = resp.data[key][i];
                            if( typeof resp.data[key][i] !== 'string' ) {
                                messagePart = JSON.stringify(resp.data[key][i]);
                            }
                            message += sep + messagePart;
                            sep = ", ";
                        }
                    }
                    messages.push(key + ": " + message);
                    $("#" + key).addClass("has-error");
                }
            }
        } else if( resp.detail ) {
            messages = [resp.detail];
        }
    }
    if( messages.length === 0 ) {
        messages = ["Error " + resp.status + ": " + resp.statusText];
    }
    showMessages(messages, "error");
};


/** Retrieves the csrf-token from a <head> meta tag.

    <meta name="csrf-token" content="{{csrf_token}}">
*/
function getMetaCSRFToken() {
    "use strict";
    var metas = document.getElementsByTagName('meta');
    for( var i = 0; i < metas.length; i++) {
        if (metas[i].getAttribute("name") == "csrf-token") {
            return metas[i].getAttribute("content");
        }
    }
    return "";
}
