# Association between alcohol consumption and incidence of dementia in current drinkers: linear and non-linear mendelian randomization analysis

[Lingling Zheng,](Delta:1_given name) [a][,][b][,][h] [Weiyao Liao,](Delta:1_surname) [c][,][h] [Shan Luo,](Delta:1_given name) [d] [Bingyu Li,](Delta:1_surname) [e] [Di Liu,](Delta:1_given name) [f] [Qingping Yun,](Delta:1_surname) [f] [Ziyi Zhao,](Delta:1_given name) [f] [Jia Zhao,](Delta:1_surname) [c] [Jianhui Rong,](Delta:1_given name) [c] [Zhiguo Gong,](Delta:1_surname) [b][,][∗∗]

[Feng Sha,](Delta:1_given name) [f] [,][∗] [and Jinling Tang](Delta:1_surname) [[a][,][f]](Delta:1_surname) [,][g]


aDepartment of Computational Biology and Medical Big Data, Shenzhen University of Advanced Technology, China
bDepartment of Computer Information Science, State Key Laboratory of Internet of Things for Smart City, University of Macau, Macau,
China
cSchool of Chinese Medicine, Li Ka Shing Faculty of Medicine, University of Hong Kong, Hong Kong SAR, China
dSchool of Public Health, Li Ka Shing Faculty of Medicine, University of Hong Kong, Hong Kong SAR, China
eSchool of Government, Shenzhen University, Shenzhen, Guangdong, China
fShenzhen Institute of Advanced Technology, Chinese Academy of Sciences, Shenzhen, Guangdong, China
gDivision of Epidemiology, The JC School of Public Health & Primary Care, The Chinese University of Hong Kong, Hong Kong SAR, China


Summary
Background Previous conventional epidemiological studies found a J-shape relationship between alcohol consumption and dementia, but this result was subject to confounding biases and reverse causation. Therefore, we aimed to
investigate the potential linear or non-linear causal association between alcohol consumption and the incident risk of
dementia in current drinkers.


Methods This study used data from the UK Biobank to investigate the relationship between alcohol consumption and
dementia risk. 313,958 White British current drinkers, who were free of dementia during 2006–2010, were followed
up until 2021. Alcohol consumption was self-reported and calculated according to the National Health Service
guideline. The primary outcome was all-cause dementia identified through hospital and mortality records. We
used multivariable Cox models with restricted cubic splines for conventional analysis and both non-linear and
linear Mendelian Randomization (MR) analyses to assess causal relationships, employing a genetic score based on
95 SNPs identified from a meta-genome-wide association study of 941,280 people from Europe.


Findings 313,958 current drinkers consumed an average of 13.6 [IQR: 7.1–25.2] units/week alcohol (men averaged
20.2 [11.1–33.9] units/week and women 9.5 [5.3–16.7] units/week). During a mean follow-up of 13.2 years, 5394
(1.7%) developed dementia. Multivariable Cox model with restricted cubic spline functions identified a J-shaped
relationship between alcohol consumption and dementia risk, with the lowest risk at 12.2 units/week. The nonlinear MR failed to identify a significant non-linear causal relationship (p = 0.45). Both individual-level (HR: 2.22
95%CI [1.06–4.66]) and summary-level (1.89 [1.53–2.32]) linear MR analyses indicated that higher genetically
predicted alcohol consumption increased dementia risk.


Interpretation This study identified a positive linear causal relationship between alcohol consumption and dementia
among current drinkers. The J-shaped association found in conventional epidemiological analysis was not supported
by non-linear MR analyses. Our findings suggested that there was no safe level of alcohol consumption for dementia.


Funding The Shenzhen Science and Technology Program and the Strategic Priority Research Program of Chinese
Academy of Sciences.


Copyright © 2024 The Author(s). Published by Elsevier Ltd. This is an open access article under the CC BY-NC-ND
license [(http://creativecommons.org/licenses/by-nc-nd/4.0/).](http://creativecommons.org/licenses/by-nc-nd/4.0/)


Keywords: Alcohol consumption; Dementia; Mendelian randomization


*Corresponding author. Shenzhen Institute of Advanced Technology, Chinese Academy of Sciences, Shenzhen, Guangdong 518055, China.
**Corresponding author. State Key Laboratory of Internet of Things for Smart City and the Department of Computer and Information Science,
University of Macau, Macau 999075, China.
E-mail addresses: [feng.sha@siat.ac.cn](mailto:feng.sha@siat.ac.cn) (F. Sha), [fstzgg@um.edu.mo](mailto:fstzgg@um.edu.mo) (Z. Gong).
hJoint first authorship.


# Articles

eClinicalMedicine
2024;76: 102810


Published Online 5
September 2024
[https://doi.org/10.](https://doi.org/10.1016/j.eclinm.2024.102810)
[1016/j.eclinm.2024.](https://doi.org/10.1016/j.eclinm.2024.102810)
[102810](https://doi.org/10.1016/j.eclinm.2024.102810)



[www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024 1


# Articles



Research in context


Evidence before this study
Previous conventional epidemiological studies found a J-shape
relationship between alcohol consumption and dementia, but
this result was subject to several biases. Mendelian
randomization (MR) analysis in genetic epidemiology studies,
is similar to a “genetic randomized control trial” due to the
random allocation of genotypes from parents to offspring,
and thus, not affected by reverse causation and is
independent of confounding factors that may influence
disease outcomes. Therefore, we searched PubMed, Web of
Science, and the Cochrane Library databases for studies
published in English from database inception to December 30,
2023, that investigated the causal relationship between
alcohol consumption and dementia risk, using the terms:
(“alcohol consumption”, “alcohol use”, or “drinking”) and
(“dementia”, or “Alzheimer”) and “mendelian randomization”.
Two previous two-sample MR studies showed that genetically
predicted alcohol consumption was not associated with
dementia. However, both analyses were based on summarylevel data and traditional linear MR, the heterogeneity of
different data source may diminish statistical efficacy and


Introduction
The estimated number of people with dementia would
increase from 57.4 million globally in 2019 to 152.8
million by 2050, [1] highlighting the pressing need for
effective preventive measures and public health strategies. Heavy drinking was recognized as a modifiable
dementia risk factor, but the impact of light-to-moderate
alcohol consumption is still under debate. [2] Ethical constraints on conducting randomized control trials in the
relation between alcohol consumption and dementia
leave conventional epidemiological studies prone to
biases. Notably, “abstainer bias” as one of selection bias,
refers to abstainers probably chose not to drink or quit
drinking for health reasons, leading to biased results. [3]

Furthermore, previous studies might exclude alcohol
consumers with early cognitive decline signs or overlook
the interaction between alcohol use and other diseases
risks leading to premature mortality before dementia
diagnosis. Consequently, evidence on the association
between light-to-moderate drinking and dementia risk is
mixed. Some studies indicate light-to-moderate drinking
is associated with lower dementia risk compared to abstainers and heavy drinkers, [4][,][5] but others find no association. [6][,][7] Further, the protective association between
light-to-moderate alcohol consumption and dementia
might be confounded by healthier lifestyle choices
prevalent among moderate drinkers or the socioeconomic factors influencing alcohol consumption patterns. Drinking behaviors are related to many lifestyle



linear MR may yield negative results if the J-shape relationship
between alcohol consumption and dementia really exists.


Added value of this study
This study employed both linear and non-linear Mendelian
randomization analyses on a large sample from the UK
Biobank, specifically focusing on current drinkers of White
British descent. Our findings contradicted the widely reported
J-shaped relationship by demonstrating a positive linear
association between alcohol consumption and the incidence
of dementia among current drinkers. This study highlighted
that no level of alcohol consumption is safe in terms of
dementia risk.


Implications of all the available evidence
MR studies clarify the causal relevance of alcohol intake with
diseases by accounting for confounding biases and reversal
causation in conventional epidemiological studies. The linear
and non-linear MR provides evidence on linear causal harmful
effects of alcohol use on dementia. This finding improves our
understanding of the adverse effects of alcohol use on
dementia among current drinkers.


factors, which couldn’t be controlled in most conventional epidemiology studies. These limitations highlighted the challenges of confounding and reverse
causality in alcohol-related epidemiology studies.
Mendelian randomization (MR) analysis in genetic
epidemiology studies, is similar to a “genetic randomized control trial” due to the random allocation of genotypes from parents to offspring, and thus, not affected
by reverse causation and is independent of confounding
factors that may influence disease outcomes. [8] Previous
MR studies assessing the relationship between alcohol
consumption and dementia were based on the linear
assumption, which did not establish a causal connection. [9][,][10] Consequently, it remains unknown whether the
observed negative association between alcohol consumption and dementia among the light-to-moderate
drinkers is causal. Non-linear MR is an extension to
standard MR that first stratifies the population based on
levels of exposure, and then conducts separate linear
MR analyses within each stratum. [11] To our knowledge,
there is no study on the non-linear causal relation between alcohol consumption and incident risk of
dementia.
This study aimed to fill this gap by conducting both
linear and non-linear MR analyses within the same
population-based cohort among current drinkers, aiming to test whether the observed protective effect of
light-to-moderate alcohol consumption and dementia is
causal. All the analyses were stratified by sex to re


2 [www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024


# Articles



estimate the association between alcohol consumption
and dementia risk.


Methods
Study design
In the present study, we first conducted a conventional
epidemiology study using a multivariable Cox model
with restricted cubic spline functions to explore the nonlinear relationship between alcohol consumption and
the risk of dementia among current drinkers. We then
further applied genetic epidemiology studies with both
non-linear and linear MR to investigate their potential
causal relationship. All analyses were stratified by
gender to account for sex-specific effects.


Study population
The UK Biobank (UKB) served as the foundation for this
study, comprising a community-based cohort of over
500,000 individuals from 22 assessment centers across
the United Kingdom, recruited between 2006 and
2010. [12] At baseline, participants provided informed
consent and a wealth of sociodemographic, clinical, genetic, and lifestyle data, including detailed accounts of
alcohol consumption. Participants were included based
on completed the alcohol consumption questionnaire
and available genetic data.
Ethnic information was self-reported by participants
at baseline. Analyses were restricted to white British
individuals to minimize potential confounding of MR
analyses by genetic ancestry. We included only current
alcohol drinkers for the following two reasons. First, this
study aimed to provide practical implications only for
drinkers, without any intention to encourage nondrinkers to consume alcohol. Second, a focus on current drinkers should limit potential selection biases and
confounding, and account for significant differences in
characteristics between drinkers and non-drinkers
(Appendix p 5–6). Thus, individuals with zero unit/
week alcohol consumption, including abstainers and
current drinkers with zero consumption were excluded.
Exclusions were applied for any mismatch between selfreported and genetic sex, chromosomal anomalies, and
cases of prevalent dementia at baseline, leaving 313,958
participants in the final analysis (The following chart
showed in Fig. 1a).


Measures of alcohol consumption
Alcohol consumption was assessed based on selfreported weekly/monthly intake of various types,
including wines, beer/cider, spirits, and others. According to the National Health Service (NHS) guidelines, weekly units were defined as follows: a drink/
week alcohol of wine = 1.5 units/week; a drink/week
alcohol of champagne plus white wine = 1.5 units/
week; a drink/week alcohol of beer/cider = 2.8 units/
week; a drink/week alcohol of spirits = 1 unit/week; a



drink/week alcohol of fortified wine = 1 unit/week; a
drink/week alcohol of others = 1.5 units/week. Total
weekly alcohol consumption was summarized across
all categories. When the weekly alcohol consumption
was not available, but the monthly alcohol consumption was available, divide the monthly alcohol consumption by 4.3 to convert to weekly alcohol
consumption. Alcohol consumption was categorized as
‘Safe’ (≤14 units/week) and ‘Unsafe” (>14 units/week)
following Alcohol Change UK and UK Department of
Health guidelines. [13]


Measures of outcome
The incidence of all-cause dementia was obtained from
UKB routinely collected healthcare data, including hospital admissions and mortality records, aligned with the
International Classification of Disease 10 codes, and
supplemented by algorithmically defined outcomes and
self-reported conditions (Appendix p 7). Utilizing the
routinely collected healthcare datasets for incident dementia is reliable, with a positive predictive value (PPV)
of 82.5%. [14] However, the positive predictive value for the
diagnosis of dementia subtypes is less reliable, with
71% for Alzheimer’s disease (AD) and 44% for vascular
dementia (VD). Consequently, this study only focused
on all-cause dementia, but did not distinguish AD and
VD due to lower diagnostic precision with UKB data.
Follow-up duration was calculated from baseline to the
earliest of first dementia diagnosis, loss to follow-up,
death, or censoring (2021-11-12).


Covariables
Covariates included sociodemographic and healthrelated variables potentially associated with dementia
risk. Gender was self-reported at baseline, and any
mismatches between self-reported and genetic sex were
excluded to maintain consistent gender categorization.
Age was divided into three categories: ≤45, (45–65], and
>65 years. Education levels were detailed as higher education/vocational (including college or university degrees and other professional qualifications), secondary
education (encompassing all stages of secondary education), and other. Socioeconomic status was determined using the Townsend deprivation index,
segmenting the cohort into least, middle, and most
deprived groups. The areas were defined in terms of
administrative boundaries (encompassing England,
Scotland, Wales, and Northern Ireland). For healthrelated variables, BMI was categorized according to
WHO guidelines into underweight (<18.5), normal
weight [18.5–25), overweight [25–30), and obese
(≥30 kg/m [2] ). Smoking status, derived from self-reports,
included never, former, and current smokers. Physical
activity was assessed through metabolic equivalent task
minutes per week, divided into insufficient, sufficient,
or additional levels based on tertiles. [15] Sleep duration
was classified into less than 6 h, 6–9 h, and more than



[www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024 3


# Articles

























Fig. 1: Selection of eligible participants and single nucleotide polymorphisms (SNP) of alcohol consumption in this study.



9 h of sleep. Presence of cardiometabolic diseases
(including myocardial infarction, heart failure, hypertension, and type 2 diabetes mellitus) and stroke at
baseline were calculated based on UKB first occurrence
or algorithm-defined outcomes. [16] Participants’ APOE ε4
allele status, a known genetic risk factor for dementia,
was identified by the presence of one or more ε4 alleles
(rs429358 and rs7412).



The genetic instrument for alcohol assumption
The alcohol consumption genetic score (Alcohol-GS)
was developed as a genetic instrument by calculating a
weighted genetic score based on 95 single nucleotide
polymorphisms (SNPs) with their respective associations with alcohol consumption. These SNPs were
selected from a comprehensive genome-wide association study (GWAS) encompassing 941,280 participants,



4 [www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024


# Articles



which identified 99 SNPs specifically linked to alcohol
consumption, confirming their specificity to alcohol
consumption without strong links to smoking behaviors. [17] Despite the UKB sample contributing to approximately 30% of the GWAS cohort, a weighted genetic
score could potentially mitigate bias. [18] The detailed SNP
selection process was shown in Fig. 1b and Appendix p
2. Each SNP was coded as 0, 1, or 2 to signify the
number of alleles linked to increased alcohol consumption. Appendix p 2–3 provided details for the
calculation of the Alcohol-GS and its assessment as a
genetic instrument adheres to three assumptions of
MR: (1) associated with alcohol consumption (log10
(unit/week); (2) not associated with confounders; (3) not
directly associated with dementia risk. The Alcohol-GS
accounted for 15.5% of the variance in logtransformed weekly alcohol consumption in the UKB,
with an F-statistics of 1228.4 (Appendix p 17).


Statistics
Alcohol consumption data were log-transformed
(log10 (unit/week)) due to their skewed distribution,
with results reported in the original unit (unit/week)
for clarity. The baseline characteristics of the participants were described by the mean and standard deviation (SD) for normal distributed continuous
variables, the median with interquartile range (IQR)
for non-normal distribution continuous variables, and
proportions for categorical variables. To identify disparities between genders, standardized differences
were calculated, with absolute values greater than 0.1
indicating significant differences between men and
women drinkers. [19]

Initially, multivariable Cox proportional hazards
models with restricted cubic spline functions were used
to assess the nonlinear relationship between alcohol
consumption groups and dementia incident risk. The
validity of the proportional hazard assumption was
confirmed using Schoenfeld residuals, with a resulting
p-value of 0.11. The model was adjusted for sex, age,
area, APOE status, education level, and socioeconomic
status. For graphical representation, the alcohol consumption level associated with the lowest risk of dementia was designated as the reference point.
Subsequently, we applied non-linear MR analysis
with a residual stratification method on log-transformed
alcohol consumption. The normal distribution of logtransforming alcohol consumption satisfied the precondition for the residual non-linear MR. Linear MR
estimations quantified localized average causal effects
across ten stratified groups based on residual alcohol
consumption levels. These estimates reflected the
localized average causal effects within each stratum,
allowing us to compare the effects of alcohol consumption across genetic backgrounds. For sensitivity
analysis, we adopted the doubly-ranked stratification
method, which offers a robust approach to address



potential violations of constant genetic effects. [20]

Furthermore, to assess the suitability of both
non-linear MR methods for alcohol consumption, we
utilized the established correlation between alcohol
consumption and alcoholic hepatitis as a positive control, while age, which is unaffected by alcohol consumption, served as a negative control. This approach
was employed to ascertain the reliability and specificity
of our findings. Further details on non-linear MR
analysis methods are available in Appendix p 3–4.
Given the lack of a non-linear MR association between alcohol consumption and dementia, we integrated individual-level and summary-level linear MR
analyses to assess the causal effect of alcohol consumption on dementia. The individual-level analysis
used Alcohol-GS as the instrument variable, aggregating
the effect size of multiple SNPs to enhance the statistical
power to detect associations. Conversely, the summarylevel analysis directly used 95 SNPs as instruments,
which could more easily assess the robust estimate and
adjust for pleiotropy.
In individual-level linear MR analysis, we fitted a
two-stage least-squares regression with Alcohol-GS to
assess the causal relationship between alcohol consumption and dementia risk. We included death as a
competing risk in a sensitivity analysis. The first stage
involved linear regression to estimate alcohol consumption (log10 (unit/week)) from Alcohol-GS, applied
with both basic and competing risk models. The second
stage utilized a Cox proportional hazards model to
evaluate the association between genetically estimated
alcohol levels and dementia risk in the basic model, with
the competing risk model further adjusted for mortality.
Adjustments in both stages included age, sex, assessment centers, genotyping arrays, and the top 20 genetic
principal components. While acknowledging the potential subgroup analyses to produce spurious association, [21] we aimed to evaluate the robustness of our
finding and verify the consistency of the direction effect
with the main result. Therefore, we conducted the
subgroup analyses by age, socioeconomic status, education level, BMI, smoke status, sleep duration, physical
activity level, and APOE ε4 status in the sensitivity
analysis.
In summary-level linear MR analysis, we obtained
SNP-specific Wald estimates (quotient of genetic association on dementia and genetic association on
alcohol consumption (log10 (unit/week)) and then
meta-analyzed them using Inverse Variance
Weighted (IVW) with multiplicative random effects.
To address directional pleiotropy, we employed
MR-Egger and the Weighted Median as sensitivity
analyses. To address the potential bias of sample
overlap in one sample, we implemented a 10-fold MR
strategy. We further performed summary-level twosample MR analysis as the sensitivity analysis
(Appendix p 4–5).



[www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024 5


# Articles



All statistical tests were estimated by 2-sided tests. A
p value less than 0.05 was considered significant. All
analyses were undertaken using R.


Ethics
The UK Biobank obtained ethical approval from the
Research Ethics Committee (REC reference 11/NW/
0382), and all participants provided written informed
consent.


Role of the funding source
The funder of the study did no participate in the design
of study, the collection, analysis, or interpretation of
data, the writing of the manuscript, or the decision to
submit the manuscript for publication.


Results
Baseline characteristic
Out of 313,958 current drinkers, 5394 individuals
(1.7%) were diagnosed with dementia during an average
follow-up year of 13.2 years (SD 2.0). The median weekly
alcohol consumption was 13.60 units (IQR 7.10–25.20).
About half of current drinkers (48.6%) exceed the UK’s
recommended alcohol intake threshold of 14 units per
week. Additionally, the cohort showed a balanced
gender distribution, but women represented the double
proportion of men in the safe alcohol consumption
group, the pattern reversed in the unsafe alcohol consumption group (Table 1).


Findings from restricted cubic spline Cox
Proportional Hazards analyses
The multivariable Cox Proportional Hazards analyses
with restricted cubic spline functions revealed a J-shaped relationship between alcohol consumption and dementia risk among overall current drinkers, with a
significant non-linear test (p = 0.04) (Fig. 2). The lowest
dementia risk was observed at an alcohol consumption
level of 11.9 units/week, which was smaller than the
recommended threshold of 14 units/week. A similar Jshape pattern appeared for men, with the lowest dementia risk at 16.8 units/week (p = 0.04). While for
women, the analysis did not reveal a significant nonlinear relationship, with minimal risk observed at 8.4
units/week.


Findings from non-linear mendelian randomization
analyses
The non-linear MR analysis showed no significant deviation from a linear relationship between genetically
predicted alcohol and dementia risk in the overall current drinkers (Non-linear test of p = 0.45). However, a
significant positive correlation was identified (p = 0.02),
with no significant heterogeneity (Cochran Q p = 0.34;
Fig. 3). Sensitivity analyses applying the double-rankly
stratification non-linear MR showed a similar result



(Appendix p 22). Appendix p 18 showed significant associations between Alcohol-GS and alcohol consumption across the strata by both non-linear MR methods.
In gender-specific analysis, no significant non-linear
correlation was observed between genetic alcohol consumption and dementia risk in either men or women (p
for non-linear test were 1.00 in men and 0.20 in women)
(Fig. 3). Men did not exhibit a statistically significant
genetic correlation with dementia risk (p = 0.43 and
Cochran Q p = 0.83). Conversely, women showed a
significant positive association but with significant heterogeneity (p = 0.005 and Cochran Q p = 0.01).
In sensitivity analyses, the positive control confirmed
a strong positive correlation (p < 0.001) between genetically predicted alcohol consumption and alcoholic liver
disease, without evidence of non-linearity or significant
heterogeneity. The negative control analysis showed no
significant association between genetically predicted
alcohol consumption and age. All these results reinforced the reliability and specificity of the non-linear MR
analysis (Appendix p 23–24).


Findings from linear mendelian randomization
analyses
The individual-level linear MR analysis provided robust
evidence that an increasing genetically predicted alcohol
consumption was associated with an increased risk of
dementia (HR 2.22 [95% CI 1.06–4.66]) among overall
drinkers. Further analysis considering competing risk
events confirmed the causal genetic relationship (3.78

[1.33–10.8]; Table 2). Subgroup sensitivity analyses
revealed consistent positive correlations across various
strata between genetically predicted alcohol consumption and dementia risk (Appendix p 19).
Summary-level linear MR as complementary analysis
identified similar findings, the effect estimates were
broadly consistent between IVW (HR 1.89 [95% CI
1.53–2.32]) and the pleiotropy robust methods as MRegger (2.35 [1.73–3.23]) and weighted median (2.41

[1.76–3.30]) in one-sample MR with a 10-fold method to
overcome the overfitting. For sensitivity analysis, we
further conducted the two-sample summary-level MR
from two independent studies to test the robustness of
the MR estimates (Appendix p 20). IVW method yielded
similar findings (1.62 [1.08–2.44]), the other two MR
methods did not reach statistical significance (MRegger: 1.60 [0.70–3.68]; weighted median MR: 1.67

[0.91–3.07]). However, they maintained the same
directional effect between genetically predicted alcohol
consumption and dementia risk, suggesting a coherent
pattern. Additionally, MR-Egger analysis in this context
also found no evidence of pleiotropy among drinkers,
reinforcing the absence of bias in our observed
associations.
Linear MR analyses underscored a positive genetic
linkage in women (HR 3.25 [95% CI 0.98–10.8]), which
was further affirmed in analyses considering competing



6 [www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024


# Articles



risks (7.73 [1.47–40.7]). Although the results for the men
were not statistically significant, the direction of effect
was consistent with the results among overall drinkers.
Summary-level MR analyses confirm a positive link
between genetically predicted alcohol intake and dementia risk across genders (Table 2).


Discussion
The conventional epidemiology analysis showed a
J-shaped association between alcohol consumption and
dementia among current drinkers. Nevertheless, the
non-linear MR analysis did not detect the non-linear
causal relationship between genetically predicted
alcohol consumption and the risk of dementia. The
linear MR analysis identified a linear causal relationship
between alcohol consumption and dementia among the
current drinkers.
In multivariable Cox regression analyses, we found
that the moderate alcohol consumption group exhibited
a protective effect with the risk of dementia, compared
with the light alcohol consumption group, and the
non-linear model result indicated a J-shaped association
between alcohol consumption and the occurrence of
dementia among current drinkers. These results are
similar to findings from the most comprehensive and
recent meta-analyses in conventional epidemiological
studies. [4][,][5][,][22] However, none of the studies recommended
the abstainers to drink for the prevention of dementia,
because these conventional studies are susceptible to
selection biases, confounding, and reverse causality and
alcohol drinking may lead to also other health problems.
Moderate drinkers might practice principles of moderation in other areas of life that live a healthier life than
others, [23] while abstinence might indicate withdrawal
from leisure activities that were not beneficial for preventing cognitive decline. [24] In particular, socioeconomic
status influenced the amount and type of alcohol
consumed, and as such, might play an important confounding role in the alcohol-dementia relationship. [25] As
mentioned before, a major bias in alcohol epidemiology
is the “abstainer bias”, referring to the phenomenon
that abstainers probably choose not to drink or quit
drinking for health reasons. Therefore, the abstainer
group may have worse health status than the light-tomoderate drinkers. To account for this bias, lifetime
abstainers were used as a reference group against
drinkers. However, as young adults who have a limiting
long-standing illness are more likely not to drink
alcohol, the life-time abstainers might also be very
different from drinkers. [26] This discrepancy can lead to
an exaggerated perception of the protective benefits of
light-to-moderate drinking. Addressing abstainer bias, a
study focusing on current alcohol drinkers found a
negative association between alcohol consumption and
cognitive function in a dose–response manner. [27] This
study highlighted the potential overestimation of





protective effects in conventional epidemiology
research. Despite this study’s focus on current drinkers
to mitigate “abstainer bias”, MR analysis provided a
supplementary viewpoint to assess the relationship between alcohol consumption and health outcomes. A
recent study presented findings indicat65ing the



[www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024 7


# Articles



Fig. 2: Association between alcohol consumption per week and dementia incidence risk among current drinkers. The analyses were
adjusted for demographic and genetic factors, including age, area, socioeconomic status, education level, and the presence of the APOE ε4
allele. The 95% confidence interval is indicated by the shaded region. A J-shaped association is apparent for both the overall cohort and male
drinkers, with a non-linear test p-value of 0.04 in each, suggesting a statistically significant pattern. Reference levels of alcohol consumption
were 11.94 units/week for all current drinkers, 16.60 units/week for men, and 8.39 units/week for women. Dashed lines represent the reference
levels and lowest level of alcohol consumption for dementia risk in each models.



absence of genetic evidence for a net protective effect of
moderate alcohol consumption on cardiovascular mortality, despite the presence of a J-shaped association in
conventional epidemiological analysis. [28]

Our non-linear MR results could not provide any
evidence to support a non-linear association between
alcohol consumption and the incidence of dementia
among current drinkers. The “instrument-free” residual
strata nonlinear MR could assess the shape of the causal
relationship between an exposure and outcome using
individual-level data, [11] which has been applied to
confirm the J-shaped relationship between BMI and
cardiovascular disease mortality. [29] To avoid the collider
bias from simply stratifying on measure exposure, the
“instrument-free” residual strata nonlinear MR calculates the residuals from regression on measure exposure
on the genetic instrument and undertaking MR analyses
in strata, then evaluates the heterogeneity of the results
among the strata and perform a test for nonlinear relationships. Although it is argued that there may be



some problems with this nonlinear MR method when
exploring the relationship between vitamin D and
mortality. [20][,][30] The reason was the residual nonlinear MR
defaults to the distribution of the measured exposure
satisfying a normal distribution to fitting regression
model on the exposure and the genetic instrument. So,
the estimates with this method were biased when
vitamin D distribution was significantly skewed. A new
nonlinear MR with double ranked strata method was
used to deal with the non-normal distribution of exposure. [31] The doubly ranked non-linear MR involves
ranking individuals based on the residuals from a
regression of the exposure on the genetic instrument,
thus creating strata without the need for strict parametric assumptions about the relationship between the
instrument and the exposure. This process ensures that
within each stratum, the instrumental variable assumptions hold true, facilitating a more reliable exploration of non-linear or heterogeneous effects. [31]

Moreover, in our study, we also used alcohol-related



Fig. 3: Association between genetically predicted alcohol consumption per week and dementia incident risk using non-linear mendelian
randomization analysis among current drinkers. The study utilized a residual-based fractional polynomial method to assess the causal effect
of alcohol consumption on dementia risk by stratifying the sample into 10 groups. The localized average causal effect was determined by
examining the gradient at each point on the curve, with shaded areas representing 95% confidence intervals. The association between
genetically predicted alcohol consumption and dementia risk was statistically evaluated using the overall p-value, while heterogeneity across
strata was assessed using the Cochran Q p-value. A random-effects model was applied if the Cochran Q p-value was less than 0.05.


8 [www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024


# Articles



liver disease and age as positive and negative control
outcomes to confirm both available residual strata and
doubly ranked strata nonlinear MR to verify the causal
relationship between alcohol consumption and
dementia.
We further performed linear MR analysis and
confirmed the linear causal relationship between
genetically predicted alcohol consumption and dementia
among current drinkers, especially among the women
drinkers. This results is inconsistent with previous twosample MR research showed that genetically predicted
alcohol consumption was not associated with dementia. [10][,][32] One MR study extracted 99 SNPs for alcohol
consumption from the same meta-GWAS with our
study, but only 41f SNP for MR analysis after a series of
refinements, including clumping, proxy searching, and
harmonizing SNPs associated with dementia from a
meta-GWAS including 17,008 cases and 371,154 controls. [32] This decrease may lead to a less comprehensive
capture of the genetic predisposition to alcohol consumption, potentially affecting the strength and accuracy of the MR analysis. Another only included three
SNPs in MR analysis, [10] which may lead to an underpowered statistical estimation and a high possibility of
false-negative outcomes. Both of these analyses were
based on summary-level data, the heterogeneity of
different data source may also diminish statistical efficacy. Contrastingly, a recent MR study aligned with our
findings, suggesting that any level of alcohol consumption adversely affected brain health and was unlikely to
mitigate Alzheimer’s Disease risk. [32] Our findings reinforce comprehensive linear MR analyses, incorporating
individual-level MR to boost statistical power and
summary-level MR to mitigate overfitting and bias from
sample overlap. These approaches addressed the heterogeneity and potential biases, providing a robust
foundation for our conclusions. This multifaceted
approach solidified the evidence base, affirming alcohol
consumption’s detrimental effects on dementia risk
across different methodological frameworks.
Our analyses found a distinctly more significant association between alcohol consumption and dementia
risk among women drinkers, a finding that can be
partially explained by the component cause model. [33] The
2020 Lancet Commission’s identification of various dementia risk factors, such as hypertension and smoking. [2]

Studies indicated that an integrative healthier lifestyle
(non-smoking, less alcohol consumption, adequate
sleep, physical activity, and a balanced diet) could prevent dementia. [34] The component cause model posits
that diseases like dementia result from various risk
factors combined to form a sufficient cause. This
framework suggested that alcohol’s impact on dementia
may be more evident in women, who typically had lower
rates of other risk factors, such as smoking, compared to
men. For men, the presence of multiple risk factors
could mask alcohol’s specific effects. A review discusses



differences in susceptibility to dementia based on lifestyle factors like smoking, excessive alcohol use, and
poor diet, further emphasizing the importance of a
comprehensive approach to understanding and
addressing the risk factors for dementia. [35] It points out
that the impact of health conditions on dementia risk
can vary by sex, with women being at a greater risk for
Alzheimer’s disease and men for vascular dementia. A
recent study provided updated estimates on the proportion of Alzheimer’s and related dementias in the US
related to modifiable risk factors. [36] It also assessed differences by sex, finding that the combined populationattributable risks were higher in men than in women
and varied by race and ethnicity.
Although many studies have found a negative association between light-to-moderate alcohol consumption
and dementia incidence, none of the hypothesized
mechanisms explaining this phenomenon has been
proved. [37] Presuming the observed benefits of alcohol
consumption on cognitive health still existed after all the
biases were addressed, the benefits may still not be the
result of ethanol but other constituents in alcoholic
beverages, such as flavonoids, resveratrol, and polyphenols. [38] The specific beneficial elements, if there are
any, should be investigated and promoted instead of
alcohol use in general. Ethanol and acetaldehyde (a











[www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024 9


# Articles



metabolite) are neurotoxic and cause central nervous
system inflammation, reduced numbers, and morphological changes in hippocampal neurons in animal
models. [39] Alcohol can also induce brain atrophy with
neuronal loss, particularly in the frontal cortex, [40] central
nervous system inflammation and epilepsy, all of which
contribute to dementia risk. [41] In a 30-year longitudinal
study, multimodal magnetic resonance imaging (MRI)
showed that even moderate alcohol intake was associated with adverse brain outcomes including hippocampal atrophy and impaired white matter microstructure. [42]

In addition, the effect of alcohol on dementia can be
indirect through diseases linked to higher intake of
alcohol and dementia, such as liver and kidney disease,
diabetes, hypertension, coronary heart disease, and
stroke. [43][–][46] Therefore, research findings concerning
alcohol use need to be interpreted with caution, as
certain conclusions favoring alcohol use may bring
about negative impact on population health in the long
run. Based on the most updated evidence, we tend to
believe that there is no safe level of alcohol consumption
for dementia.
We used a MR study design to assess the causal associations between genetically predicted alcohol consumption and dementia among current drinkers. This
design could minimize the potential biases due to confounding and reverse causality in conventional epidemiology analyses. Application of both linear and non-linear
MR analyses allows for a comprehensive assessment of
the relationship, including the exploration of potential
non-linear effects, thereby addressing the debated protective impact of light-to-moderate alcohol consumption
on dementia risk. Consistent findings across linear and
nonlinear MR analyses strengthened the evidence for the
causal adverse effects of genetically predicted alcohol
consumption and all-cause dementia.
The results of this study should be interpreted in
conjunction with some limitations. First, our study was
the reliance on self-reported alcohol consumption,
which might introduce bias. Although self-reported data
may be prone to recall inaccuracies, evidence indicates
that such errors do not markedly undermine the validity
of genetic epidemiological associations. A study in the
UK Biobank found significant genome-wide associations for self-reported alcohol consumption, suggesting
a genetic basis for these self-reports and implicating
genes involved in alcohol metabolism and neurobiology
of substance use. [47] Second, another limitation to
consider was the change in alcohol consumption over
time. Previous research using data from the Whitehall II
project explored the relationship between changes in
alcohol consumption and dementia risk, finding results
consistent with studies based on a single time point
measurement. [22] This consistency suggested that
although alcohol consumption patterns may change
over time, the impact on dementia risk remained significant, supporting the relevance of our findings. Third,



the use of dementia diagnoses derived from electronic
health records could be seen as a limitation, given the
potential for misclassification. However, only if under
recording occurred more in participants who drink less,
the association observed in this study would be overestimated. We found no evidence to support this
assumption. Fourth, UKB was selective, participants
were early-late-life people of European ancestry with
higher average levels of educational attainment and
general health. However, in this study, we performed
sensitivity analyzes that demonstrated the robustness of
our findings. At the same time, many associations
observed in other studies could be replicated in the UK
Biobank, suggesting that selection bias, if existent in
this study, is not greater than that in others. This study
identifies a positive linear causal relationship between
alcohol consumption and dementia among current
drinkers. However, their J-shaped association found in
observational studies is not supported by non-linear
Mendelian randomization analyses. The lower risk of
dementia observed among the light-to-moderate alcohol
drinkers may be due to several epidemiological biases.
We tend to believe that there is no safe level of alcohol
consumption for dementia among current drinkers.
And our study’s focus on White British individuals for
reducing genetic confounding, limits the generalizability to other racial and ethnic groups. Future research
should include more diverse populations to better understand the implications of alcohol consumption on
dementia risk. Finally, our analysis was restricted to
current drinkers, which may limit the generalizability of
our findings. By excluding non-drinkers and former
drinkers, we focused on a more homogeneous study
population, aiming to reduce variability and potential
confounding factors related to past drinking behaviors.
However, this approach means our results may not be
applicable to those who have never consumed alcohol or
who have quit drinking due to health reasons or other
factors. Our findings are intended to inform current
drinking behaviors and we do not aim to give any suggestions to non-drinkers.


Contributors
FS, LLZ and WYL contributed to study conception and design, with
development of genetic risk scores and statistical analysis led by JLT and
ZGG. FS and LLZ accessed and verified the underlying data. LLZ carried
out primary data analysis. LLZ completed the statistical analysis under
supervision of FS, JLT, and ZGG. JLT, and ZGG supervised the project.
FS, LLZ and WYL wrote the first draft of the manuscript. All authors
contributed to critical revision and editing of the manuscript, and have
approved the final version. JLT, FS and LLZ were responsible for the
decision to submit the manuscript. FS, LLZ and WYL contributed
equally, and are guarantors. The corresponding author attests that all
listed authors meet authorship criteria and that no others meeting the
criteria have been omitted.


Data sharing statement
The current study was conducted using the UK Biobank resource under
application No. 80476. All raw and derived data in this study are available from the UK Biobank [(http://www.ukbiobank.ac.uk/).](http://www.ukbiobank.ac.uk/)



10 [www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024


# Articles



Declaration of interests
All authors declare no competing interests.


Acknowledgements
This study was partly supported by the Shenzhen Science and Technology Program (grant No. KQTD20190929172835662) and the Strategic Priority Research Program of Chinese Academy of Sciences (grant
No. XDB 38040200). We thank the UK Biobank participants. All authors
would like to express our sincere gratitude to all men and women who
participated in the UK Biobank study, and the investigators, research
associates, and wider teams involved in these studies. During the
preparation of this work the authors used ChatGPT at [chatgpt.com](http://chatgpt.com) tool
to enhance the fluency of expression. After using this tool, the authors
reviewed and edited the content as needed and take full responsibility
for the content of the publication.


Appendix A. Supplementary data
Supplementary data related to this article can be found at [https://doi.](https://doi.org/10.1016/j.eclinm.2024.102810)
[org/10.1016/j.eclinm.2024.102810.](https://doi.org/10.1016/j.eclinm.2024.102810)


References
1 GBDDF Collaborators. [Estimation](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref1) of the global prevalence of dementia in 2019 and forecasted [prevalence](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref1) in 2050: an analysis for
the Global Burden of Disease [Study](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref1) 2019. Lancet Public Health.
[2022;7(2):e105–e125.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref1)
2 [Livingston G, Huntley J, Sommerlad A, et al. Dementia prevention,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref2)
intervention, and care: 2020 [report](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref2) of the Lancet Commission.
Lancet. [2020;396(10248):413–446.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref2)
3 Rehm J, Spuhler T. [Measurement](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref3) error in alcohol consumption:
the Swiss Health Survey. Eur J Clin Nutr. 1993;47(Suppl 2):
[S25–S30.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref3)
4 [Liu Y, Mitsuhashi T, Yamakawa M, et al. Alcohol consumption and](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref4)
incident dementia in older [Japanese](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref4) adults: the Okayama Study.
Geriatr Gerontol Int. 2019;19(8):740–746.
5 [Jeon KH, Han K, Jeong SM, et al. Changes in alcohol consumption](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref5)
[and risk of dementia in a nationwide cohort in South Korea. JAMA](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref5)
Netw Open. [2023;6(2):e2254771.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref5)
6 Heffernan M, Mather KA, Xu J, et al. Alcohol consumption and
incident dementia: evidence [from](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref6) the sydney memory and ageing
study. J Alzheimers [Dis.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref6) 2016;52(2):529–538.
7 Langballe EM, Ask H, Holmen [J,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref7) et al. Alcohol consumption and
risk of dementia up to 27 years [later](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref7) in a large, population-based
sample: the HUNT study, [Norway.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref7) Eur J Epidemiol. 2015;30(9):
[1049–1056.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref7)
8 Davey Smith G, Ebrahim S. [What](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref8) can mendelian randomisation
[tell us about modifiable behavioural and environmental exposures?](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref8)
BMJ. [2005;330(7499):1076–1079.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref8)
9 Luo J, Thomassen JQ, [Bellenguez](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref9) C, et al. Genetic associations
[between modifiable risk factors and alzheimer disease. JAMA Netw](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref9)
Open. [2023;6(5):e2313734.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref9)
10 Larsson SC, Traylor M, [Malik](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref10) R, Dichgans M, Burgess S,
Markus HS. Modifiable [pathways](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref10) in Alzheimer’s disease: mendelian randomisation [analysis.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref10) BMJ. 2017;359:j5375.
11 Staley JR, Burgess S. [Semiparametric](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref11) methods for estimation of a
nonlinear exposure-outcome [relationship](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref11) using instrumental variables with application to [Mendelian](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref11) randomization. Genet Epidemiol. [2017;41(4):341–352.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref11)
12 Sudlow C, Gallacher J, Allen N, [et](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref12) al. UK biobank: an open access
resource for identifying the [causes](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref12) of a wide range of complex
diseases of middle and old age. PLoS Med. 2015;12(3):e1001779.
13 [NHS. The risks of drinking too much; 2022. https://www.nhs.uk/live-](https://www.nhs.uk/live-well/alcohol-advice/the-risks-of-drinking-too-much/)
[well/alcohol-advice/the-risks-of-drinking-too-much/.](https://www.nhs.uk/live-well/alcohol-advice/the-risks-of-drinking-too-much/)
14 Wilkinson T, Schnier C, Bush [K,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref14) et al. Identifying dementia outcomes in UK Biobank: a [validation](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref14) study of primary care, hospital
[admissions and mortality data. Eur J Epidemiol. 2019;34(6):557–565.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref14)
15 [Li J, Zheng L, Chan KHK, et al. Sex hormone-binding globulin and](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref15)
risk of coronary heart disease [in](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref15) men and women. Clin Chem.
[2023;69(4):374–385.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref15)
16 [Yun Q, Wang S, Chen S, et al. Constipation preceding depression:](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref16)
a population-based cohort [study.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref16) EClinicalMedicine. 2024;67:
[102371.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref16)
17 Liu MZ, Jiang Y, Wedow R, et [al.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref17) Association studies of up to 1.2
million individuals yield new [insights](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref17) into the genetic etiology of
tobacco and alcohol use. [Nat](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref17) Genet. 2019;51(2):237–244.



18 Fang S, Hemani G, Richardson TG, Gaunt TR, Davey Smith G.
Evaluating and implementing [block](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref18) jackknife resampling Mendelian randomization to mitigate [bias](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref18) induced by overlapping samples. Hum Mol [Genet.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref18) 2023;32(2):192–203.
19 Mamdani M, Sykora K, Li P, [et](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref19) al. Reader’s guide to critical
[appraisal of cohort studies: 2. Assessing potential for confounding.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref19)
BMJ. [2005;330(7497):960–962.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref19)
20 Burgess S, Wood AM, [Butterworth](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref20) AS. Mendelian randomisation
and vitamin D: the importance [of](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref20) model assumptions   - authors’
reply. Lancet Diabetes [Endocrinol.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref20) 2023;11(1):15–16.
21 Davies NM, Holmes MV, [Davey](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref21) Smith G. Reading Mendelian
randomisation studies: a guide, glossary, and checklist for clinicians. BMJ. [2018;362:k601.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref21)
22 Sabia S, Fayosse A, Dumurgier [J,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref22) et al. Alcohol consumption and
risk of dementia: 23 year [follow-up](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref22) of Whitehall II cohort study.
BMJ. [2018;362:k2927.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref22)
23 Peters R, Peters J, Warner J, Beckett N, Bulpitt C. Alcohol,
dementia and cognitive decline [in](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref23) the elderly: a systematic review.
Age Ageing. [2008;37(5):505–512.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref23)
24 Li B, Bi J, Wei C, Sha F. [Specific](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref24) activities and the trajectories of
cognitive decline among [middle-aged](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref24) and older adults: a five-year
longitudinal cohort study. J [Alzheimers](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref24) Dis. 2021;80(3):1039–1050.
25 Collins SE. Associations [between](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref25) socioeconomic factors and
alcohol outcomes. Alcohol [Res](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref25) Curr Rev. 2016;38(1):83–94.
26 [Ng Fat L, Shelton N. Associations between self-reported illness and](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref26)
non-drinking in young adults. [Addiction.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref26) 2012;107(9):1612–1620.
27 Hassing LB. Light alcohol [consumption](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref27) does not protect cognitive
function: a longitudinal [prospective](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref27) study. Front Aging Neurosci.
[2018;10:81.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref27)
28 Millwood IY, Im PK, Bennett [D,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref28) et al. Alcohol intake and causespecific mortality: conventional and genetic evidence in a prospective cohort study of 512 [000](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref28) adults in China. Lancet Public
Health. [2023;8(12):e956–e967.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref28)
29 Sun YQ, Burgess S, Staley [JR, et al. Body](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref29) mass index and all cause
mortality in HUNT [and UK Biobank studies: linear and non-linear](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref29)
mendelian randomisation [analyses.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref29) BMJ. 2019;364:l1042.
30 Wade KH, Hamilton FW, [Carslake](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref30) D, Sattar N, Davey Smith G,
Timpson NJ. Challenges in [undertaking](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref30) nonlinear Mendelian
randomization. Obesity. 2023;31(12):2887–2890.
31 Tian H, Mason AM, Liu C, [Burgess](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref31) S. Relaxing parametric
assumptions for non-linear [Mendelian](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref31) randomization using a
doubly-ranked stratification [method.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref31) PLoS Genet. 2023;19(6):
[e1010823.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref31)
32 Andrews SJ, Goate A, Anstey [KJ.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref32) Association between alcohol
[consumption and Alzheimer’s disease: a Mendelian randomization](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref32)
study. Alzheimers [Dement.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref32) 2020;16(2):345–353.
33 Rothman KJ, Greenland S, [Lash](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref33) TL. Modern epidemiology. Philadelphia: Wolters Kluwer [Health/Lippincott](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref33) Williams & Wilkins;
[2008.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref33)
34 Ward DD, Ranson JM, Wallace [LMK,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref34) Llewellyn DJ, Rockwood K.
Frailty, lifestyle, genetics and [dementia](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref34) risk. J Neurol Neurosurg
Psychiatry. [2022;93(4):343–350.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref34)
35 Podcasy JL, Epperson CN. [Considering](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref35) sex and gender in Alzheimer disease and other [dementias.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref35) Dialogues Clin Neurosci.
[2016;18(4):437–446.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref35)
36 Nianogo RA, [Rosenwohl-Mack](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref36) A, Yaffe K, Carrasco A,
Hoffmann CM, Barnes DE. Risk factors associated with alzheimer
disease and related dementias by sex and race and ethnicity in the
US. JAMA Neurol. [2022;79(6):584–591.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref36)
37 Wiegmann C, Mick I, Brandl [EJ,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref37) Heinz A, Gutwinski S. Alcohol
[and dementia - what is the link? A systematic review. Neuropsychiatr](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref37)
Dis Treat. [2020;16:87–99.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref37)
38 Haseeb S, Alexander B, [Baranchuk](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref38) A. Wine and cardiovascular
health: a comprehensive [review.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref38) Circulation. 2017;136(15):
[1434–1448.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref38)
39 Anton PE, Rutt LN, [Kaufman](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref39) ML, Busquet N, Kovacs EJ,
McCullough RL. Binge ethanol [exposure](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref39) in advanced age elevates
neuroinflammation and early [indicators](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref39) of neurodegeneration and
cognitive impairment in [female](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref39) mice. Brain Behav Immun.
[2024;116:303–316.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref39)
40 Harper C. The neuropathology [of](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref40) alcohol-related brain damage.
Alcohol Alcohol. [2009;44(2):136–140.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref40)
41 Samokhvalov AV, Irving H, [Mohapatra](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref41) S, Rehm J. Alcohol consumption, unprovoked seizures, [and](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref41) epilepsy: a systematic review
and meta-analysis. [Epilepsia.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref41) 2010;51(7):1177–1184.
42 Topiwala A, Allan CL, [Valkanova](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref42) V, et al. Moderate alcohol
consumption as risk factor for [adverse](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref42) brain outcomes and cognitive decline: longitudinal [cohort](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref42) study. BMJ. 2017;357:j2353.



[www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024 11


# Articles



43 [Berger I, Wu S, Masson P, et al. Cognition in chronic kidney disease: a](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref43)
systematic review and [meta-analysis.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref43) BMC Med. 2016;14(1):206.
44 [Kim HM, Lee YH, Han K, et al. Impact of diabetes mellitus and chronic](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref44)
[liver disease on the incidence of dementia and all-cause mortality among](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref44)
[patients with dementia. Medicine (Baltimore). 2017;96(47):e8753.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref44)
45 Kuzma E, Lourida I, Moore [SF,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref45) Levine DA, Ukoumunne OC,
Llewellyn DJ. Stroke and [dementia](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref45) risk: a systematic review and
meta-analysis. Alzheimers [Dement.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref45) 2018;14(11):1416–1426.



46 Wolters FJ, Segufa RA, [Darweesh](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref46) SKL, et al. Coronary heart
disease, heart failure, and the [risk](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref46) of dementia: a systematic review and meta-analysis. [Alzheimers](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref46) Dement. 2018;14(11):1493–
[1504.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref46)
47 Clarke TK, Adams MJ, Davies [G,](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref47) et al. Genome-wide association
study of alcohol consumption [and](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref47) genetic overlap with other
health-related traits in UK [Biobank](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref47) (N=112 117). Mol Psychiatry.
[2017;22(10):1376–1384.](http://refhub.elsevier.com/S2589-5370(24)00389-4/sref47)



12 [www.thelancet.com](http://www.thelancet.com) Vol 76 October, 2024


