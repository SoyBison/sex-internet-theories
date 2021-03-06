---
author: Coen D. Needell
title: Computational Treatise on Urban Legends
draft: true
tags: ['Machine Learning', 'Cultural Patterns', 'Urban Legends', 'Internet Culture', 'Digital Archaeology']
header-includes:
  - |
    ```{=latex}
    \usepackage{ragged2e}
    \raggedright
    ```
geometry: margin=3cm
---

# Computational Treatise on Urban Legends
## Introduction


We have to focus our attention though and draw boundaries between legend, fake news, conspiracy theory, conjecture, and so on **(There are probably more things that we need to distinguish urban legends from)**. We are all fully aware that the systems that make the Internet a breeding ground for urban legend, also make it a fantastic substrate for the other types of rumor and hearsay [@Slenderboi]. For our purposes, we will consider the genre of "Urban Legend" to be defined by the fact that the people who spread the legend know that it isn't true **(Hopefully you can find a better definition somewhere)**. Conspiracy theories tend to be spread by the true believers, and fake news tends not to be spread by people, but by robots **(This isn't entirely true, there are a lot of people who talk about conspiracy theories without believing them)**. In addition, the Urban Legend tends to take place in a fuzzy time-frame, the near past **(elaborate)**. Conspiracy theories either exist in a sharp time frame, like the Kennedy Assassination, or they exist in the present **(This seems like an important distinction, make it more clear)**. Fake News on the other hand always exists in the Now, and often includes a Call-To-Action which forces it to be mixed up in current events **(Again, maybe find some prior work on fake news)**. In addition, the star characters in Fake News and Conspiracy Theory are celebrities, senators, presidents. [@Frank_2011] Urban Legend stars the everyman, the friend of a friend, the weird uncle, but it also stars some hard-to-understand entity, like a fairy, an alien, slenderman, or a large company's incomprehensible legal policies. 


But let's focus for a moment on that third millennium (and also the decade leading up to it). The human experiment (although mostly the western countries and Japan), had just been linked to one another through the Internet. Before Google created the "clearnet", before Facebook acquired every social forum, we had specified forums, on separate sites, operated by separate people. We had Usenet, a social media system built out of email and simple text-based servers **(include a better explanation of what usenet was)**. In a time before Google, or even Snopes, you couldn't fact check that troll's rant, and those rants spread like wildfire.[@dunn2005rumors] [@donovan2004no] Even in the later times of transition, we saw legends like the story of slenderman , video game related legends like "Herobrine", and so on. Obviously we see the scarier legends show up on forums dedicated to horror (slenderman) **(slenderman technically came from an all-purpose forum, but in a thread about "creepy photoshop")**, we see video game legends sprout up out of those games' communities, and we see less intense legends appear in more general use communities **(define what you mean by this)**[@blank2007examining].  This brings us to the question: How do Urban Legends spread through online communities, and how do those communities effect the nature of the legend itself?

<!-- Fact Check all of the claims, and get examples for the "less intense" legends. -->

## Methods

### Data Sources

Much of the early internet is made available to us. Groups like the Internet Archive host repositories full of early internet interactions. Many of the forums that people used to discuss broad topics are still existing, and keep their old posts up for posterity **(we need to get a better idea of how limited this resources is)**. That being said, this is far from complete, IRC (Internet Relay Chat) logs will be mostly wiped from the record. IRC servers were often private, and hosted by private entities. In addition, the Usenet archive that will be used for this discussion is not complete, it is however very comprehensive for the boards that it exists for, and this includes the largest boards. By compiling usenet records, we see a very large section of the picture. We will be able to see links between individuals, and links between communities [@archive]. If we add into this data sources like forum archives, we will be able to construct a much larger picture. **(Once you actually do it, remember to come back and make the methods section more specific, cite specific data sources, so on)**

Using text classification methods, we can sift through these posts, and pick out a selection of urban legends that we will use to study their dynamics overall. Then, we can find posts that reference those legends. Conceptually, we can imagine that posts fit into one of three categories, irrelevant, which consists of posts that do not reference the urban legend at all, carrier, which consists of posts that reference the story in passing, but don't tell the story, and spreader, which consists of posts that tell the legend, thus spreading it to other people in the community. We can imagine that a single user can write posts that belong to all of these categories, but each individual post can only belong to one. **(Flesh out the theory a little more, cite common characteristics in post types.)**

### Analysis

Using those three categories above, we would construct a temporal model of spread through the network that will let us understand how the legend spreads overall. This is a contagion model of ideas that is based off of the idea that the individuals in the community are exposed to a legend, and then spread it for some amount of time, before they get bored of it and stop. In addition, we can use topic modeling to create a set of features for all of the spreader posts for all of the urban legends that we're studying, and see how the spreader posts change their telling of the story based on the community that they're talking to. For example, we'd expect the story of slenderman to take on a different tone in an anthropology focused community than it would in a parenting focused community. **(Be more comprehensive about how that contagion model works)**

Ideally the topics that we deconstruct from the spreader post serve as analogues for the "genes" in the Darwinian model of idea spread [@Dawkins_1989] [@Kronfeldner_2014]. Under this theory, we would expect that the topics in a spreader post will change as the legend interacts with a new substrate, a specific type of community **(Citation Needed)**. We may even be able to detect a difference in the story as the legend spreads between usenet and the forum-space. We would also expect that some stories are less prone to mutation than others. For example, there is a certain subgenre of scary story that appeared on the early internet called "creepy pasta" which is a mutation of "copy pasta" which is in turn a mutation of "copy paste". These are stories which mostly appeared in the same format, implying that a person spreading the story would be copying the story from the place that they first saw it, and pasting it to a new post. While "Creepy Pasta" have died down over the years, and now the term is synonymous with internet scary stories, "copy pasta" is still a core part of how internet communities interact, with many of the famous copy pasta becoming memes of their own, often mutating in such a way that they change topics entirely, but keep the cadence and tone of the original. **(Citation Needed, possibly irrelevant information.)**

If the Darwinian model is accurate, we should expect the topics that make up an Urban Legend to change when the story is introduced to a new environment. Ideally the topics that change will be in some way connected to the new substrate's nature. For example we would expect the version of an urban legend on an academic community to make more reference to complex ideas and theory, whereas in it's original substrate, the language would likely be more general. **(Citation Needed)**

## Results

<!-- Results go here --->

## Discussion
<!-- Analysis of results goes here --->

## Conclusion

<!-- Conclusion -->

---

# References

