import {assign_config, ProjectConfig} from "./config.js"

let log_state = true;
const PROJECT_VER = ''
const PROJECT_VER_READABLE = ''
let static_title = ''
$(document).ready(async function () {

    // Resizing window to needed size
    window.resizeTo(838, 576);
    window.addEventListener("resize", function () {
        window.resizeTo(838, 576);
    });
    await eel.get_exe_name()(async (name) => {
        static_title = name + " | Comments";
    });
    // Authenticating with HWID only
    await eel.get_hwid()(async (hwid) => {
        static_title += (PROJECT_VER ? (" v" + PROJECT_VER) : "") + " " + hwid;
        document.title = static_title;
        console.log("HWID:", hwid);

        // Проверяем HWID
        eel.check_license(hwid)().then((licenseResult) => {
            console.log("Результат проверки лицензии:", licenseResult, typeof licenseResult);
        
            if (licenseResult === false) {
                // HWID НЕ найден в списке - отправляем в бота и блокируем
                console.log("HWID не найден в списке, отправляю уведомление и блокирую");
                eel.send_license(hwid)();
                block();
            } else if (licenseResult === true) {
                // HWID найден в списке - разрешаем работу
                console.log("HWID найден в списке, доступ разрешен");
            } else if (licenseResult === null) {
                // Ошибка подключения к серверу - блокируем, но НЕ отправляем в бота
                console.log("Ошибка подключения к серверу лицензий, блокирую доступ");
                block();
            }
        }).catch((error) => {
            console.error("Ошибка при проверке лицензии:", error);
            block();
        });
});

    // Load config
    // await fetch('data/config.json')
    //     .then(response => response.json())
    //     .then(jsonResponse => assign_config(jsonResponse));
    eel.read_file("data/config.json")((result) => {
        assign_config(JSON.parse(result));
        load_config();
        // Select option handling
        $('select').each(function () {
            $(this).on('change', select_change.bind($(this)[0]));
            if ($(this)[0].id.endsWith('posts')) {
                $(this)[0].selectedIndex = 3;
                return;
            }
            $(this)[0].selectedIndex = 2;
        }).change();
    });
    // Checkboxes handling
    $('[type=checkbox]').each(function () {
        $(this).on('change', checkbox_onchange.bind($(this)[0]));
    });

    // Text inputs handling
    $('[type=text]').each(function () {
        $(this).on('input', input_onchange.bind($(this)[0]));
    });
    // File button handling
    $('.file-lines-button').each(function () {
        $(this).on('click', from_file.bind($(this)[0]));
    });
    // File picture button handling
    $('.photo-file-button').each(function () {
        $(this).on('click', picture_from_file.bind($(this)[0]));
    });
    // Folder picture button handling
    $('.photo-folder-button').each(function () {
        $(this).on('click', picture_from_folder.bind($(this)[0]));
    });
    // Start button handling
    $('#start').each(function () {
        $(this).on('click', start);
    });
    $('#openconsole').each(function () {
        $(this).on('click', openconsole);
    });
    // Start button handling
    $('#addacc').each(function () {
        $(this).on('click', addacc);
    });
    $('#changeproxy').each(function () {
        $(this).on('click', add_proxy);
    });
    // Left sidebar button handling
    $('.left-sidebar-button-panel img').each(function () {
        $(this).on('click', handle_menu_button.bind($(this)[0]));
    });
    log('Проект запущен!')
    // No pointer at start
    document.activeElement.blur();
});
eel.expose(block);

function block() {
    console.log("Вызвана функция block()"); // Для отладки
    
    const bannedElement = document.querySelector(".banned");
    const undertextElement = document.querySelector(".undertext");
    
    if (bannedElement && undertextElement) {
        console.log("Элементы найдены, показываю блок лицензии"); // Для отладки
        
        // Показываем блок лицензии
        bannedElement.style.visibility = "visible";
        
        let seconds_left = 10;
        undertextElement.innerHTML = "Неверный ключ программы. Выход через " + seconds_left + " секунд";
        
        const countdown = setInterval(() => {
            seconds_left--;
            undertextElement.innerHTML = "Неверный ключ программы. Выход через " + seconds_left + " секунд";
            
            if (seconds_left <= 0) {
                clearInterval(countdown);
                console.log("Закрываю окно"); // Для отладки
                window.close();
            }
        }, 1000);
    } else {
        console.error("Элементы .banned или .undertext не найдены!");
        // Резервный вариант
        alert("Ваша лицензия недействительна!");
        setTimeout(() => window.close(), 3000);
    }
}

eel.expose(log);
eel.expose(log_warning);
eel.expose(log_error);
eel.expose(log_progstate);

async function _log(newString, color, sender = PROJECT_VER_READABLE) {
    let time = await eel.get_time()();

    var divElement = document.getElementById('log-context');
    var isScrolledToBottom = divElement.scrollHeight - divElement.clientHeight <= divElement.scrollTop + 1;

    var newSpanElement = document.createElement('span');
    newSpanElement.style.color = color;

    // Создаем элемент времени
    let timeSpan = document.createElement('span');
    timeSpan.textContent = time + ' ';
    newSpanElement.appendChild(timeSpan);

    // Создаем ссылку на отправителя
    if (sender && sender.trim()) {
    let senderLink = document.createElement('a');
    senderLink.textContent = sender;
    senderLink.href = 'tg://resolve?phone=' + sender;
    senderLink.target = '_blank';
    senderLink.style.color = color;
    newSpanElement.appendChild(document.createTextNode('['));
    newSpanElement.appendChild(senderLink);
    newSpanElement.appendChild(document.createTextNode(']: '));

        }
// Парсим текст на ссылки
    var regex = /\[([^\]]+)\]\(([^)]+)\)/g;
    let lastIndex = 0;
    let match;
    let plainText = ""; // Для текста без markdown

    while ((match = regex.exec(newString)) !== null) {
        let beforeLinkText = newString.substring(lastIndex, match.index);
        newSpanElement.appendChild(document.createTextNode(beforeLinkText));
        plainText += beforeLinkText + match[2]; // Добавляем текст без markdown

        // Создаем элемент ссылки
        let link = document.createElement('a');
        link.textContent = match[2]; // Текст ссылки
        link.href = match[1];        // URL
        link.target = '_blank';
        link.style.color = color;
        newSpanElement.appendChild(link);

        lastIndex = regex.lastIndex;
    }

    // Добавляем оставшийся текст после последней ссылки
    if (lastIndex < newString.length) {
        let remainingText = newString.substring(lastIndex);
        newSpanElement.appendChild(document.createTextNode(remainingText));
        plainText += remainingText;
    }

    // Добавляем в лог
    divElement.appendChild(newSpanElement);
    divElement.appendChild(document.createElement('br'));

    var statusElement = document.getElementById('status');
    statusElement.textContent = (sender && sender.trim()) ? `${time} [${sender}]: ${plainText.trim()}` : `${time} ${plainText.trim()}`;

    if (isScrolledToBottom) {
        divElement.scrollTop = divElement.scrollHeight - divElement.clientHeight;
    }
}


// async function _log(newString, color, sender = PROJECT_VER_READABLE) {
//     let time = await eel.get_time()();

//     var divElement = document.getElementById('log-context');
//     var isScrolledToBottom = divElement.scrollHeight - divElement.clientHeight <= divElement.scrollTop + 1;

//     var newSpanElement = document.createElement('span');
//     newSpanElement.style.color = color;

//     // Создаем элемент времени
//     let timeSpan = document.createElement('span');
//     timeSpan.textContent = time + ' ';
//     newSpanElement.appendChild(timeSpan);

//     // Создаем ссылку на отправителя
//     let senderLink = document.createElement('a');
//     senderLink.textContent = sender;
//     senderLink.href = 'tg://resolve?phone=' + sender;
//     senderLink.target = '_blank';
//     senderLink.style.color = color;
//     newSpanElement.appendChild(document.createTextNode('['));
//     newSpanElement.appendChild(senderLink);
//     newSpanElement.appendChild(document.createTextNode(']: '));

//     // Парсим текст на ссылки
//     var regex = /\[([^\]]+)\]\(([^)]+)\)/g;
//     let lastIndex = 0;
//     let match;

//     while ((match = regex.exec(newString)) !== null) {
//         // Добавляем текст до ссылки
//         newSpanElement.appendChild(document.createTextNode(newString.substring(lastIndex, match.index)));

//         // Создаем элемент ссылки
//         let link = document.createElement('a');
//         link.textContent = match[2]; // Текст ссылки
//         link.href = match[1];        // URL
//         link.target = '_blank';
//         link.style.color = color;
//         newSpanElement.appendChild(link);

//         lastIndex = regex.lastIndex;
//     }

//     // Добавляем оставшийся текст после последней ссылки
//     if (lastIndex < newString.length) {
//         newSpanElement.appendChild(document.createTextNode(newString.substring(lastIndex)));
//     }

//     // Добавляем в лог
//     divElement.appendChild(newSpanElement);
//     divElement.appendChild(document.createElement('br'));

//     var statusElement = document.getElementById('status');
//     statusElement.textContent = `${time} [${sender}]: ${newString}`;

//     if (isScrolledToBottom) {
//         divElement.scrollTop = divElement.scrollHeight - divElement.clientHeight;
//     }
// }

function link_to_span(link, hint, color) {
    let a_elem = document.createElement('a');
    a_elem.textContent = hint
    a_elem.setAttribute('href', link)
    a_elem.setAttribute('target', '_blank')
    a_elem.style.color = color
    return a_elem
}

function log(newString, sender = PROJECT_VER_READABLE) {
    _log(newString, '#cfd4d9', sender)
}

function log_warning(newString, sender = PROJECT_VER_READABLE) {
    _log(newString, '#ffeb3b', sender)
}

function log_error(newString, sender = PROJECT_VER_READABLE) {
    _log(newString, '#f44336', sender)
}

function log_progstate(newString, sender = PROJECT_VER_READABLE) {
    _log(newString, '#4caf50', sender)
}

async function start() {
    await eel.start_button()();
}

function openconsole() {
    if (!log_state) {
        $(".main-context")[0].style.visibility = 'hidden';
        $("#log-context")[0].style.visibility = 'visible';
        $("#openconsole")[0].innerHTML = '▼';
    } else {
        $(".main-context")[0].style.visibility = 'visible';
        $("#log-context")[0].style.visibility = 'hidden';
        $("#openconsole")[0].innerHTML = '▲';
    }
    log_state = !log_state;
}

function addacc() {
    eel.get_phone_code(prompt('Введите номер телефона от аккаунта: '))();
}

async function add_proxy(){ try{ console.warn('Прокси отключены'); }catch(e){} return; }

eel.expose(ask_phone_code)

function ask_phone_code() {
    return parseInt(prompt("Введите код подтверждения Telegram: "))
}

eel.expose(ask_2fa)


function ask_2fa() {
    return prompt("Введите пароль двухэтапной аутентификации: ")
}

eel.expose(refresh_title)

function refresh_title(opened, closed, age, sent, code) {
    let code_text = ''
    if (code !== 0)
        code_text = 'КОД ВХОДА: ' + code + ' | '
    document.title = code_text + static_title + ' | КАНАЛОВ:' + (opened + closed) + ' ОТКР:' + opened + ' ЗАКР:' + closed + ' ТРАСТ:' + age + ' ОТПР:' + sent
}


function handle_menu_button() {
    $('.left-sidebar-button-panel img').each(function () {
        $(this)[0].className = "";
        $(this)[0].src = $(this)[0].src.replace('_blue.png', '.png')
    });
    if (this.className === "active-lsc") {
        return;
    }
    this.className = "active-lsc";
    this.src = this.src.replace('.png', '_blue.png')
}

function load_config() {
    /* Loading checkboxes */
    ProjectConfig.profile.enabled ? $("#profile-checkbox-active").attr("checked", "checked") : $("#profile-checkbox-active").removeAttr("checked");
    ProjectConfig.profile.hidden ? $("#hidden-checkbox-active").attr("checked", "checked") : $("#hidden-checkbox-active").removeAttr("checked");
    ProjectConfig.profile.fa ? $("#2fa-checkbox-active").attr("checked", "checked") : $("#2fa-checkbox-active").removeAttr("checked");
    ProjectConfig.autoposts.enabled ? $("#posts-checkbox-active").attr("checked", "checked") : $("#posts-checkbox-active").removeAttr("checked");
    ProjectConfig.autoposts.uniqalize ? $("#posts-checkbox-uniqalize").attr("checked", "checked") : $("#posts-checkbox-uniqalize").removeAttr("checked");
    ProjectConfig.autojoin.enabled ? $("#autojoin-checkbox-active").attr("checked", "checked") : $("#autojoin-checkbox-active").removeAttr("checked");
    ProjectConfig.autojoin.all ? $("#all-checkbox-active").attr("checked", "checked") : $("#all-checkbox-active").removeAttr("checked");
    ProjectConfig.autocomments.enabled ? $("#autocomments-checkbox-active").attr("checked", "checked") : $("#autocomments-checkbox-active").removeAttr("checked");
    ProjectConfig.autocomments.uniqalize ? $("#autocomments-checkbox-uniqalize").attr("checked", "checked") : $("#autocomments-checkbox-uniqalize").removeAttr("checked");
	ProjectConfig.autojoin.delete_folders ? $("#delete-folders-checkbox-active").attr("checked", "checked") : $("#delete-folders-checkbox-active").removeAttr("checked");
    /* Loading selects */
    ProjectConfig.profile.first_name.forEach((elem) => {
        $("#pr_sel_name")[0].appendChild(new Option(elem, undefined, false, true));
    });
    ProjectConfig.profile.last_name.forEach((elem) => {
        $("#pr_sel_surname")[0].appendChild(new Option(elem, undefined, false, true));
    });
    ProjectConfig.profile.username.forEach((elem) => {
        $("#pr_sel_uname")[0].appendChild(new Option(elem, undefined, false, true));
    });
    ProjectConfig.profile.bio.forEach((elem) => {
        $("#pr_sel_bio")[0].appendChild(new Option(elem, undefined, false, true));
    });
    ProjectConfig.autoposts.posts.forEach((elem) => {
        $("#po_sel_posts")[0].appendChild(new Option(elem, undefined, false, true));
    });
    ProjectConfig.autocomments.posts.forEach((elem) => {
        $("#aco_sel_posts")[0].appendChild(new Option(elem, undefined, false, true));
    });
    ProjectConfig.autojoin.channels.forEach((elem) => {
        $("#aj_sel_channels")[0].appendChild(new Option(elem, undefined, false, true));
    });
    ProjectConfig.autoposts.channels.forEach((elem) => {
        $("#po_sel_channels")[0].appendChild(new Option(elem, undefined, false, true));
    });


    /* Loading inputs */
    $("#aj_in_delay")[0].value = ProjectConfig.autojoin.delay;
    $("#po_in_count")[0].value = ProjectConfig.autoposts.count;
    $("#po_in_delay")[0].value = ProjectConfig.autoposts.delay;
}

async function picture_from_file() {
    const path = this.id === 'acpic' ? "channel_pics" : "profile_pics";
    let fileHandle = await window.showOpenFilePicker({
        types: [
            {
                description: 'Picture',
                accept: {
                    'image/png': [],
                    'image/jpeg': []
                }
            },
        ],
        excludeAcceptAllOption: true,
        multiple: false
    });
    const file = await fileHandle[0].getFile();
    let reader = new FileReader();
    reader.onloadend = function () {
        eel.add_picture(new Uint8Array(reader.result).toString(), path)();
    }
    reader.readAsArrayBuffer(file);

}

async function picture_from_folder() {
    const path = this.id === 'acpic' ? "channel_pics" : "profile_pics";
    let dirHandle = await window.showDirectoryPicker();
    for await(let handle of dirHandle.values()) {
        if (!handle.name.endsWith('.jpg') && !handle.name.endsWith('.png')) {
            continue
        }
        let reader = new FileReader();
        reader.onloadend = function () {
            eel.add_picture(new Uint8Array(reader.result).toString(), path)();
        }
        const file = await handle.getFile();
        reader.readAsArrayBuffer(file);
    }
}

async function checkbox_onchange() {
    if (this.id === "profile-checkbox-active") ProjectConfig.profile.enabled = this.checked;
    if (this.id === "2fa-checkbox-active") ProjectConfig.profile.fa = this.checked;
    if (this.id === "hidden-checkbox-active") ProjectConfig.profile.hidden = this.checked;
    if (this.id === "channel-checkbox-active") ProjectConfig.channel.enabled = this.checked;
    if (this.id === "autocomments-checkbox-active") ProjectConfig.autocomments.enabled = this.checked;
    if (this.id === "autocomments-checkbox-uniqalize") ProjectConfig.autocomments.uniqalize = this.checked;
    if (this.id === "posts-checkbox-active") ProjectConfig.autoposts.enabled = this.checked;
    if (this.id === "posts-checkbox-uniqalize") ProjectConfig.autoposts.uniqalize = this.checked;
    if (this.id === "autojoin-checkbox-active") ProjectConfig.autojoin.enabled = this.checked;
    if (this.id === "all-checkbox-active") ProjectConfig.autojoin.all = this.checked;
	if (this.id === "delete-folders-checkbox-active") ProjectConfig.autojoin.delete_folders = this.checked;

    await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
}

async function input_onchange() {
    if (this.id === "aj_in_delay") {
        ProjectConfig.autojoin.delay = this.value;
        await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
        return;
    }
    if (this.id === "po_in_count") {
        ProjectConfig.autoposts.count = this.value;
        await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
        return;
    }
    if (this.id === "po_in_delay") {
        ProjectConfig.autoposts.delay = this.value;
        await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
        return;
    }
    let select = this.nextElementSibling;
    let selected_option = $(select).find(":selected");
    selected_option.text(this.value);
    let options = $(select).find("option").toArray();
    options.forEach(function callback(option, index, array) {
        array[index] = option.innerText;
    });
    let splice_count = (select.id === "aco_sel_posts" || select.id === "po_sel_posts") ? 3 : 2;
    options.splice(0, splice_count);
    switch (select.id) {
        case "pr_sel_name":
            ProjectConfig.profile.first_name = options;
            break;
        case "pr_sel_surname":
            ProjectConfig.profile.last_name = options;
            break;
        case "pr_sel_uname":
            ProjectConfig.profile.username = options;
            break;
        case "pr_sel_bio":
            ProjectConfig.profile.bio = options;
            break;
        case "ac_sel_title":
            ProjectConfig.channel.title = options;
            break;
        case "po_sel_posts":
            ProjectConfig.autoposts.posts = options;
            break;
        case "aj_sel_channels":
            ProjectConfig.autojoin.channels = options;
            break;
        case "po_sel_channels":
            ProjectConfig.autoposts.channels = options;
            break;
        case "aco_sel_posts":
            ProjectConfig.autocomments.posts = options;
            break;
        //String.Raw
    }
    await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
}

async function select_change() {
    let input = this.previousElementSibling;
    if (this.id.endsWith('posts')) {
        switch (this.selectedIndex) {
            case 0:
                let text = window.prompt('Текст поста:');
                let delay = window.prompt('Задержка:', '0');
                this.appendChild(new Option(`(${delay}s) ${text}`, undefined, false, true));
                break;
            case 1:
                let prompt = window.prompt('Запрос к ИИ (текст поста - %p): ', 'Отреагируй 1 предложением на это, не упоминая что ты ИИ: %p');
                let wait = window.prompt('Задержка:', '0');
                this.appendChild(new Option(`AI (${wait}s) ${prompt}`, undefined, false, true));
                break;
            case 2:
                for (let i = this.options.length - 1; i >= 3; i--) {
                    this.options[i].remove();
                }
                this.appendChild(new Option('(0s) Новое', undefined, false, true));
                break;
        }
        let options = $(this).find("option").toArray();
        options.forEach(function callback(option, index, array) {
            array[index] = option.innerText;
        });
        options.splice(0, 3);
        switch (this.id) {
            case "aco_sel_posts":
                ProjectConfig.autocomments.posts = options;
                break;
            case "ac_sel_posts":
                ProjectConfig.channel.posts = options;
                break;
        }

        await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
        input.value = this.value;
        input.focus()
        return;
    }
    switch (this.selectedIndex) {
        case 0:
            this.appendChild(new Option('Новое', undefined, false, true));
            break;
        case 1:
            for (let i = this.options.length - 1; i >= 2; i--) {
                this.options[i].remove();
            }
            this.appendChild(new Option('Новое', undefined, false, true));
            break;
    }
    let options = $(this).find("option").toArray();
    options.forEach(function callback(option, index, array) {
        array[index] = option.innerText;
    });
    options.splice(0, 2);

    switch (this.id) {
        case "pr_sel_name":
            ProjectConfig.profile.first_name = options;
            break;
        case "pr_sel_surname":
            ProjectConfig.profile.last_name = options;
            break;
        case "pr_sel_bio":
            ProjectConfig.profile.bio = options;
            break;
        case "ac_sel_title":
            ProjectConfig.channel.title = options;
            break;
        case "ac_sel_bio":
            ProjectConfig.channel.about = options;
            break;
        case "ac_sel_username":
            ProjectConfig.channel.username = options;
            break;
        case "aj_sel_channels":
            ProjectConfig.autojoin.channels = options;
            break;
        case "po_sel_channels":
            ProjectConfig.autoposts.channels = options;
            break;
    }
    await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
    input.value = this.value;
    input.focus()
}

async function from_file() {
    let fileHandle = await window.showOpenFilePicker({
        types: [{
            description: 'Текстовый файл',
            accept: {'text/txt': ['.txt']}
        },], excludeAcceptAllOption: true, multiple: false
    });
    const file = await fileHandle[0].getFile();
    const content = await file.text();
    const content_lines = content.split('\r\n');
    switch (this.id) {
        case "autojoin-channels-button":
            content_lines.forEach(function (elem) {
                $("#aj_sel_channels")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.autojoin.channels = ProjectConfig.autojoin.channels.concat(content_lines);
            break;
        case "posts-channels-button":
            content_lines.forEach(function (elem) {
                $("#po_sel_channels")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.autoposts.channels = ProjectConfig.autojoin.channels.concat(content_lines);
            break;
        case "profile-names-button":
            content_lines.forEach(function (elem) {
                $("#pr_sel_name")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.profile.first_name = ProjectConfig.profile.first_name.concat(content_lines);
            break;
        case "profile-surnames-button":
            content_lines.forEach(function (elem) {
                $("#pr_sel_surname")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.profile.last_name = ProjectConfig.profile.last_name.concat(content_lines);
            break;
        case "profile-bios-button":
            content_lines.forEach(function (elem) {
                $("#pr_sel_bio")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.profile.bio = ProjectConfig.profile.bio.concat(content_lines);
            break;
        case "channel-titles-button":
            content_lines.forEach(function (elem) {
                $("#ac_sel_title")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.channel.title = ProjectConfig.channel.title.concat(content_lines);
            break;
        case "channel-bios-button":
            content_lines.forEach(function (elem) {
                $("#ac_sel_bio")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.channel.about = ProjectConfig.channel.about.concat(content_lines);
            break;
        case "channel-usernames-button":
            content_lines.forEach(function (elem) {
                $("#ac_sel_username")[0].appendChild(new Option(elem, undefined, false, true));
            });
            ProjectConfig.channel.username = ProjectConfig.channel.username.concat(content_lines);
            break;
    }
    let edited_select = this.previousElementSibling.children[1];
    $("#" + edited_select.id).each(() => {
        $(this)[0].selectedIndex = $("#" + edited_select.id + " option").length - 1;
    }).change();
    await eel.write_file("data/config.json", JSON.stringify(ProjectConfig));
}

eel.expose(close_project);

function close_project() {
    window.close()
}

window.addEventListener("beforeunload", function (e) {
    eel.kill();
});
let delstartflag = true;
document.getElementById("start").addEventListener("contextmenu", function (event) {
    if (delstartflag) {
        event.preventDefault();
        let res = prompt("Введите время в формате ЧЧ:ММ или количество секунд до запуска");
        eel.delayed_start(res)();
        delstartflag = false;
    }
});
eel.expose(start_timing);

function start_timing(delay) {
    $("#start")[0].innerHTML = delay
}

function hideProxyUI(){try{const el=document.querySelector('#changeproxy'); if(el) el.style.display='none';}catch(e){}}
window.addEventListener('DOMContentLoaded', hideProxyUI);