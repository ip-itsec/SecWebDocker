FROM php:7.1-fpm

RUN docker-php-ext-install mysqli && \
    docker-php-ext-install pdo_mysql

COPY src /var/www/app
