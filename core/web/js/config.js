class Config {
    constructor(proxies, profile, autoposts, autocomments, autojoin) {
        this.proxies = proxies;
        this.profile = profile;
        this.autoposts = autoposts;
        this.autocomments = autocomments;
        this.autojoin = autojoin;
    }

    to_string() {
        return JSON.stringify(this);
    }

    link_checkbox(checkbox, prop) {
        prop = checkbox.checked;
    }
}

class ProfileConfig {
    constructor(enabled, fa, hidden, first_name, last_name, username, bio, photo) {
        this.enabled = enabled;
        this.fa = enabled;
        this.hidden = hidden;
        this.first_name = first_name;
        this.last_name = last_name;
        this.username = username;
        this.bio = bio;
        this.photo = photo;
    }
}

class AutoPostsConfig {
    constructor(enabled, uniqalize, count, posts) {
        this.enabled = enabled;
        this.uniqalize = uniqalize;
        this.count = count;
        this.posts = posts;
    }
}

class AutoCommentsConfig {
    constructor(enabled, uniqalize, posts) {
        this.enabled = enabled;
        this.uniqalize = uniqalize;
        this.posts = posts;
    }
}

class AutoJoinConfig {
    constructor(enabled, delay, channels, all, delete_folders = false) {
        this.enabled = enabled;
        this.delay = delay;
        this.channels = channels;
        this.all = all;
        this.delete_folders = delete_folders; // Добавлено новое поле
    }
}

class TextPost {
    constructor(delay, text) {
        this.delay = delay;
        this.channels = text;
    }
}

let ProfileCfg = new ProfileConfig(false, false, ['Настя', 'Света'], ['Макс', 'Маск'], ['Успех', 'Success'], 'photo/');
let AutoPostsCfg = new AutoPostsConfig(true, true, 0, null);
let AutoCommentsCfg = new AutoCommentsConfig(true, true, null);
let AutoJoinCfg = new AutoJoinConfig(true, 0, ['https://t.me/+PEy9zS5ie-A3MGJi'], false, false) // Добавлен параметр delete_folders
export let ProjectConfig = new Config(null, ProfileCfg, AutoPostsCfg, AutoCommentsCfg, AutoJoinCfg);

export function assign_config(new_config) {
    ProjectConfig = new_config;
    console.log('Config assigned!');
}