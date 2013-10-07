<!DOCTYPE html>
<html lang="fr">
<head>
    <title>TuxPanel</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="/static/reset.css" />
    <link rel="stylesheet" href="/static/design.css" />
</head>
<body>
    <header>
        <div id="logo">
            <h1>TuxPanel</h1>
        </div>
        <nav>
            <ul>
                % for panel in utils.get_root_panels():
                    <li>
                        <a href="/${panel.model.short_name}/">
                            <img src="/static/images/nav/${panel.model.short_name}.png"
                                alt="${panel.model.display_name}" />
                        </a>
                    </li>
                % endfor
                <li><a href="/support/" title="${_('Support')}">
                    <img src="/static/images/nav/support.png" alt="${_('Support')}"/></a>
                </li>
                <li><a href="/user/" title="${_('Your Account')}">
                    <img src="/static/images/nav/user.png" alt="${_('Your Account')}"/></a>
                </li>
                <li><a href="/user/logout" title="${_('Logout')}" class="navlogout">
                    <img src="/static/images/nav/logout.png" alt="${_('Logout')}"/></a>
                </li>
            </ul>
        </nav>
        <div style="clear:both"></div>
    </header>
    <div class="wrap">
        <aside>
            <%block name="sidemenu"></%block>
        </aside>
        <section>
            <div class="content">
                <div id="messages">
                    % for m in request.session.pop_flash():
                        <p>${m}</p>
                    % endfor
                </div>
                ${self.body()}
            </div>
        </section>
    </div>
</body>
</html>

