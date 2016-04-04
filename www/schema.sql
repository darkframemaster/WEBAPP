drop database if exists darkframexue;
create database darkframexue;

use darkframexue;

grant select,insert,update,delete on darkframexue.* to 'root'@'localhost' identified by 'xh1008';

create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `password` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `create_at` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`create_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs(
	`id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`summary` varchar(200) not null,
	`content` mediumtext not null,
	`create_at` real not null,
	key `idx_create_at`(`create_at`),
	primary key(`id`)
)engine=innodb default charset=utf8;
	
create table comments(
	`id` varchar(50) not null,
	`blog_id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`content` mediumtext not null,
	`create_at` real not null,
	key `idx_create_at`(`create_at`),
	primary key(`id`)
)engine=innodb default charset=utf8;


