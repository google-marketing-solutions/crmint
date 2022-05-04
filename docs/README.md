## CRMint Docs

To test the documentation locally:

1.  Local install of [Jekyll](https://jekyllrb.com/):

    ```shell
    $ gem install bundler
    $ echo "source 'https://rubygems.org'
    $ gem 'github-pages', group: :jekyll_plugins" > Gemfile
    $ bundle install
    ```

1.  Server the `docs` locally :

    ```shell
    $ cd docs/
    $ bundle exec jekyll serve
    ```
