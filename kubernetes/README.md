## Kubernetes deployment

1. Start with changing configMap values in `configmap.yaml` file according to your setup (namespaces, names, credentials).

    Deploy config map: 
   `kubectl create -f configmap.yaml`

2. Run initial job to build index and populate data.

    `kubectl create -f job-create.yaml`

    It will provide script with 2 optional arguments, --days=-1 to index all data and --rebuild to create index in Elasticsearch.

3. Schedule cron job to update only last 24 hours of data.

    `kubectl create -f cronjob-update.yaml`

### Kibana

You can deploy Kibana:

`kubectl create -f kibana.yaml`

and expose it to the public using (nginx) ingress with username/password authentication.

Firstly, generate auth file and load it as a secret:

```
htpasswd -c auth.txt mytardis
kubectl -n mytardis create secret generic reporting --from-file=auth.txt
rm auth.txt
```

Secondly, deploy ingress with annotation to use secret:

`kubectl create -f ingress.yaml`

### Vouch Proxy

[Vouch Proxy](https://github.com/vouch/vouch-proxy) will allow you to restrict access to Kibana instance using number of oAuth providers, like Google, Okta, etc.

Modify `vouch.yaml` setting file according to your desired setup (domain names you want to use, which auth provider to use and its config, while-list of allowed emails).

Add Vouch repository to your Helm:

`helm repo add halkeye https://halkeye.github.io/helm-charts/`

Install Vouch to the cluster:

`helm install halkeye/vouch --version 0.2.1 -f vouch.yaml --namespace ingress-nginx --name vouch`

Inspect and modify `ingress-vouch.yaml` according to your setup and deploy (nginx) ingress with Vouch:

`kubectl create -f ingress-vouch.yaml`

If something gone wrong, remove Vouch from the cluster:

`helm del --purge vouch`
